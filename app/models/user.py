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

    # 组织架构相关字段
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), index=True)  # 所属部门
    leader_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)  # 角色负责人
    role_type = db.Column(db.String(20), default='general')  # 角色类型: general, management, technical, business
    description = db.Column(db.Text)  # 角色描述

    # 关系 - 明确指定外键避免冲突
    department = db.relationship('Department', backref='roles')
    leader = db.relationship('User', foreign_keys=[leader_id], backref='led_roles')

    # 重新定义users关系，明确指定外键
    users = db.relationship('User', backref='role', lazy='dynamic',
                           foreign_keys='User.role_id')

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
        # 确保permissions是整数类型
        try:
            permissions_int = int(self.permissions) if self.permissions is not None else 0
            return permissions_int & perm == perm
        except (ValueError, TypeError):
            return False

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

    # 2FA (Two-Factor Authentication) fields
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(32))  # TOTP secret key
    backup_codes = db.Column(db.Text)  # JSON string of backup codes
    two_factor_setup_date = db.Column(db.DateTime)

    # Leader relationships
    leader_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)  # 直属上级
    is_department_leader = db.Column(db.Boolean, default=False)  # 是否是部门领导
    is_project_manager = db.Column(db.Boolean, default=False)   # 是否是项目经理

    # Relationships
    sessions = db.relationship('UserSession', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    # Organization relationships
    leader = db.relationship('User', remote_side=[id], backref='subordinates')

    # 组织架构关系 - 明确指定外键避免冲突
    department_memberships = db.relationship('UserDepartment', back_populates='user',
                                           primaryjoin="User.id == UserDepartment.user_id",
                                           foreign_keys='[UserDepartment.user_id]',
                                           lazy='dynamic', cascade='all, delete-orphan')
    project_memberships = db.relationship('UserProject', back_populates='user',
                                        primaryjoin="User.id == UserProject.user_id",
                                        foreign_keys='[UserProject.user_id]',
                                        lazy='dynamic', cascade='all, delete-orphan')
    workspace_memberships = db.relationship('UserWorkspace', back_populates='user',
                                          primaryjoin="User.id == UserWorkspace.user_id",
                                          foreign_keys='[UserWorkspace.user_id]',
                                          lazy='dynamic', cascade='all, delete-orphan')

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

    # 2FA (Two-Factor Authentication) methods
    def generate_totp_secret(self):
        """生成TOTP密钥并保存到用户对象"""
        import pyotp
        import base64
        import secrets

        # 生成16字节的随机密钥
        secret = base64.b32encode(secrets.token_bytes(16)).decode('utf-8')

        # 保存到用户对象
        self.two_factor_secret = secret

        return secret

    def generate_totp_qr_code(self, secret, issuer_name="Enterprise Wiki"):
        """生成TOTP QR码"""
        import pyotp
        import qrcode
        import io
        import base64

        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=self.email,
            issuer_name=issuer_name
        )

        # 生成QR码
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(totp_uri)
        qr.make(fit=True)

        # 将QR码转换为base64字符串
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return img_str

    def verify_totp_token(self, token):
        """验证TOTP令牌"""
        import pyotp
        import time
        from flask import current_app

        if not self.two_factor_secret:
            current_app.logger.error(f"TOTP: User {self.id} has no two_factor_secret")
            return False

        try:
            totp = pyotp.TOTP(self.two_factor_secret)
            current_time = int(time.time())
            current_app.logger.info(f"TOTP: User {self.id} verifying token {token} against secret {self.two_factor_secret} at time {current_time}")

            result = totp.verify(token, valid_window=1)  # 允许1个时间窗口的误差
            current_app.logger.info(f"TOTP: User {self.id} verification result: {result}")
            return result
        except Exception as e:
            current_app.logger.error(f"TOTP: User {self.id} verification error: {str(e)}")
            return False

    def generate_backup_codes(self):
        """生成备用恢复码"""
        import secrets
        import json

        # 生成8个6位数的备用码
        backup_codes = []
        for _ in range(8):
            code = f"{secrets.randbelow(1000000):06d}"
            backup_codes.append(code)

        # 存储为JSON字符串
        self.backup_codes = json.dumps(backup_codes)
        self.two_factor_setup_date = datetime.utcnow()

        return backup_codes

    def verify_backup_code(self, code):
        """验证备用恢复码"""
        import json

        if not self.backup_codes:
            return False

        try:
            backup_codes = json.loads(self.backup_codes)
            if code in backup_codes:
                # 使用后删除备用码
                backup_codes.remove(code)
                self.backup_codes = json.dumps(backup_codes)
                return True
        except (json.JSONDecodeError, TypeError):
            pass

        return False

    def enable_two_factor(self, secret):
        """启用双因素认证"""
        self.two_factor_secret = secret
        self.two_factor_enabled = True
        self.generate_backup_codes()

    def disable_two_factor(self):
        """禁用双因素认证"""
        self.two_factor_enabled = False
        self.two_factor_secret = None
        self.backup_codes = None
        self.two_factor_setup_date = None

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

    # Organization and Leadership methods
    def would_create_leader_cycle(self, leader_id):
        """检查设置leader是否会造成循环依赖"""
        if leader_id is None or leader_id == 0:
            return False

        # 不能设置自己为leader
        if leader_id == self.id:
            return True

        # 检查潜在的leader是否是自己的下级
        from app.models.organization import Department, UserDepartment, Project, UserProject

        potential_leader = User.query.get(leader_id)
        if not potential_leader:
            return False

        # DFS检查是否会造成循环
        stack = [potential_leader]
        visited = set()

        while stack:
            current = stack.pop()
            if current.id in visited:
                continue

            visited.add(current.id)
            if current.id == self.id:
                return True  # 会造成循环

            # 检查直属下级
            for subordinate in current.subordinates:
                if subordinate.id not in visited:
                    stack.append(subordinate)

            # 检查部门领导关系
            dept_memberships = UserDepartment.query.filter_by(
                user_id=current.id,
                is_active=True
            ).all()
            for membership in dept_memberships:
                if membership.department and membership.department.leader_id == current.id:
                    # 获取部门所有成员
                    for member in membership.department.members:
                        if member.user.id not in visited and member.is_active:
                            stack.append(member.user)

            # 检查项目管理关系
            proj_memberships = UserProject.query.filter_by(
                user_id=current.id,
                is_active=True
            ).all()
            for membership in proj_memberships:
                if membership.project and membership.project.manager_id == current.id:
                    # 获取项目所有成员
                    for member in membership.project.members:
                        if member.user.id not in visited and member.is_active:
                            stack.append(member.user)

        return False

    def get_all_subordinates(self):
        """获取所有下级用户（包括间接下级）"""
        all_subordinates = set()
        stack = [self]
        visited = set()

        while stack:
            current = stack.pop()
            if current.id in visited:
                continue

            visited.add(current.id)

            # 添加直属下级
            for subordinate in current.subordinates:
                if subordinate.id not in visited:
                    all_subordinates.add(subordinate)
                    stack.append(subordinate)

            # 添加通过部门领导关系的下级
            from app.models.organization import Department, UserDepartment
            dept_memberships = UserDepartment.query.filter_by(
                user_id=current.id,
                is_active=True
            ).all()
            for membership in dept_memberships:
                if membership.department and membership.department.leader_id == current.id:
                    for member in membership.department.members:
                        if member.user.id not in visited and member.is_active and member.user.id != current.id:
                            all_subordinates.add(member.user)
                            stack.append(member.user)

            # 添加通过项目管理关系的下级
            from app.models.organization import Project, UserProject
            proj_memberships = UserProject.query.filter_by(
                user_id=current.id,
                is_active=True
            ).all()
            for membership in proj_memberships:
                if membership.project and membership.project.manager_id == current.id:
                    for member in membership.project.members:
                        if member.user.id not in visited and member.is_active and member.user.id != current.id:
                            all_subordinates.add(member.user)
                            stack.append(member.user)

        return list(all_subordinates)

    def get_leader_chain(self):
        """获取领导链，从直接上级到最高级领导"""
        leaders = []
        current_user = self
        visited = set()

        while current_user and current_user.id not in visited:
            visited.add(current_user.id)

            # 检查直属上级
            if current_user.leader_id:
                direct_leader = User.query.get(current_user.leader_id)
                if direct_leader and direct_leader.id not in visited:
                    leaders.append(direct_leader)
                    current_user = direct_leader
                    continue

            # 检查部门领导
            from app.models.organization import UserDepartment
            dept_membership = UserDepartment.query.filter_by(
                user_id=current_user.id,
                is_active=True
            ).first()

            if dept_membership and dept_membership.department:
                dept_leader = dept_membership.department.leader
                if dept_leader and dept_leader.id not in visited:
                    leaders.append(dept_leader)
                    current_user = dept_leader
                    continue

            # 检查项目经理
            from app.models.organization import UserProject
            proj_membership = UserProject.query.filter_by(
                user_id=current_user.id,
                is_active=True
            ).first()

            if proj_membership and proj_membership.project:
                proj_manager = proj_membership.project.manager
                if proj_manager and proj_manager.id not in visited:
                    leaders.append(proj_manager)
                    current_user = proj_manager
                    continue

            break

        return leaders

    def can_manage_user(self, target_user):
        """检查是否可以管理目标用户"""
        if self.is_administrator():
            return True

        # 不能管理自己
        if self.id == target_user.id:
            return False

        # 检查是否在领导链中
        return self in target_user.get_leader_chain()

    def get_departments(self):
        """获取用户所属的所有部门"""
        return [membership.department for membership in self.department_memberships
                if membership.is_active and membership.department]

    def get_projects(self):
        """获取用户参与的所有项目"""
        return [membership.project for membership in self.project_memberships
                if membership.is_active and membership.project]

    def get_workspaces(self):
        """获取用户可访问的所有工作区"""
        workspaces = set()

        # 添加直接加入的工作区
        for membership in self.workspace_memberships:
            if membership.is_active and membership.workspace:
                workspaces.add(membership.workspace)

        # 添加通过部门获得权限的工作区
        from app.models.organization import Workspace
        for department in self.get_departments():
            dept_workspaces = Workspace.query.filter_by(
                department_id=department.id,
                is_active=True
            ).all()
            workspaces.update(dept_workspaces)

        # 添加通过项目获得权限的工作区
        for project in self.get_projects():
            proj_workspaces = Workspace.query.filter_by(
                project_id=project.id,
                is_active=True
            ).all()
            workspaces.update(proj_workspaces)

        return list(workspaces)

    def update_leader_status(self):
        """更新用户的领导状态标志"""
        from app.models.organization import Department, Project

        # 检查是否是部门领导
        led_dept = Department.query.filter_by(leader_id=self.id, is_active=True).first()
        self.is_department_leader = bool(led_dept)

        # 检查是否是项目经理
        managed_proj = Project.query.filter_by(manager_id=self.id, is_active=True).first()
        self.is_project_manager = bool(managed_proj)

        db.session.add(self)

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