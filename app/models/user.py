from datetime import datetime, timedelta
from flask_login import UserMixin, AnonymousUserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import current_app
from app import db, login_manager
import hashlib

class Permission:
    FOLLOW = 0x01
    COMMENT = 0x02
    WRITE = 0x04
    MODERATE = 0x08
    ADMIN = 0x80
    VIEW_PRIVATE = 0x10
    EDIT_ALL = 0x20
    DELETE_ALL = 0x40

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    def __repr__(self):
        return f'<Role {self.name}>'

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        self.permissions = 0

    def has_permission(self, perm):
        return self.permissions & perm == perm

    @staticmethod
    def insert_roles():
        roles = {
            'Viewer': [Permission.FOLLOW, Permission.COMMENT, Permission.VIEW_PRIVATE],
            'Editor': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE, Permission.VIEW_PRIVATE],
            'Moderator': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE,
                         Permission.MODERATE, Permission.VIEW_PRIVATE, Permission.EDIT_ALL],
            'Administrator': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE,
                            Permission.MODERATE, Permission.ADMIN, Permission.VIEW_PRIVATE,
                            Permission.EDIT_ALL, Permission.DELETE_ALL]
        }
        default_role = 'Viewer'
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    avatar_hash = db.Column(db.String(32))
    avatar = db.Column(db.String(500))  # 自定义头像URL
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)

    # Relationships
    sessions = db.relationship('UserSession', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config.get('ADMIN_EMAIL', 'admin@company.com'):
                self.role = Role.query.filter_by(name='Administrator').first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = self.gravatar_hash()

    def __repr__(self):
        return f'<User {self.username}>'

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'confirm': self.id}, salt='confirm')

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, salt='confirm', max_age=3600)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'reset': self.id}, salt='reset')

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, salt='reset', max_age=3600)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        return True

    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'change_email': self.id, 'new_email': new_email}, salt='email-change')

    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, salt='email-change', max_age=3600)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = self.gravatar_hash()
        db.session.add(self)
        return True

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        return self.can(Permission.ADMIN)

    def is_locked(self):
        return self.locked_until and self.locked_until > datetime.utcnow()

    def lock_account(self, hours=24):
        self.locked_until = datetime.utcnow() + timedelta(hours=hours)
        db.session.add(self)

    def unlock_account(self):
        self.locked_until = None
        self.failed_login_attempts = 0
        db.session.add(self)

    def increment_failed_login(self):
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:  # Lock after 5 failed attempts
            self.lock_account(hours=24)
        db.session.add(self)

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def gravatar_hash(self):
        return hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()

    def get_avatar(self, size=100, default='identicon', rating='g'):
        """获取用户头像，优先使用自定义头像，否则使用Gravatar"""
        if self.avatar and self.avatar.strip():
            return self.avatar.strip()
        # 如果没有自定义头像，使用Gravatar
        return self.gravatar(size=size, default=default, rating=rating)

    def gravatar(self, size=100, default='identicon', rating='g'):
        # 总是使用HTTPS URL来避免请求上下文问题
        url = 'https://secure.gravatar.com/avatar'
        hash = self.avatar_hash or self.gravatar_hash()
        return f'{url}/{hash}?s={size}&d={default}&r={rating}'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'name': self.name,
            'role': self.role.name if self.role else None,
            'member_since': self.member_since.isoformat() if self.member_since else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'is_active': self.is_active
        }

    def get_notification_settings(self):
        """获取用户的通知设置"""
        import json
        if hasattr(self, 'notification_settings') and self.notification_settings:
            try:
                return json.loads(self.notification_settings)
            except (json.JSONDecodeError, AttributeError):
                pass

        # 返回默认设置
        return {
            'email_notifications': True,
            'watch_notifications': True,
            'mention_notifications': True,
            'comment_notifications': True,
            'daily_digest': False
        }

    def set_notification_settings(self, settings):
        """设置用户的通知偏好"""
        import json
        try:
            # 如果数据库中没有这个字段，我们需要添加
            if not hasattr(self, 'notification_settings'):
                # 这里可以考虑使用数据库迁移来添加字段
                # 为了简化，我们暂时跳过这个功能
                return

            self.notification_settings = json.dumps(settings)
        except Exception as e:
            print(f"Error setting notification preferences: {e}")

    def should_receive_notification(self, notification_type):
        """检查用户是否应该接收特定类型的通知"""
        settings = self.get_notification_settings()

        # 如果总开关关闭，不发送任何邮件
        if not settings.get('email_notifications', True):
            return False

        # 检查具体的通知类型
        type_mapping = {
            'watch': 'watch_notifications',
            'mention': 'mention_notifications',
            'comment': 'comment_notifications'
        }

        setting_key = type_mapping.get(notification_type)
        if setting_key:
            return settings.get(setting_key, True)

        return True  # 默认发送

    def get_safe_datetime(self, field_name):
        """安全地获取datetime字段，处理可能的字符串类型"""
        field_value = getattr(self, field_name, None)
        if field_value is None:
            return None

        # 如果已经是datetime对象，直接返回
        if hasattr(field_value, 'strftime'):
            return field_value

        # 如果是字符串，尝试解析
        if isinstance(field_value, str):
            try:
                from datetime import datetime
                # 处理ISO格式字符串
                if field_value.endswith('Z'):
                    field_value = field_value[:-1] + '+00:00'
                dt = datetime.fromisoformat(field_value)
                # 移除时区信息以便使用
                if dt.tzinfo:
                    return dt.replace(tzinfo=None)
                return dt
            except (ValueError, AttributeError):
                return None

        return None

class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False

login_manager.anonymous_user = AnonymousUser

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class UserSession(db.Model):
    __tablename__ = 'user_sessions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    session_token = db.Column(db.String(64), unique=True, index=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    def __init__(self, **kwargs):
        super(UserSession, self).__init__(**kwargs)
        if self.expires_at is None:
            self.expires_at = datetime.utcnow() + timedelta(hours=24)

    def is_expired(self):
        return datetime.utcnow() > self.expires_at

    def revoke(self):
        self.is_active = False
        db.session.add(self)

def request_is_secure():
    from flask import request
    return request.is_secure