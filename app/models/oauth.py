from datetime import datetime
from app import db


class OAuthProvider(db.Model):
    """OAuth提供者配置"""
    __tablename__ = 'oauth_providers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # google, github, microsoft, etc.
    display_name = db.Column(db.String(100), nullable=False)  # 显示名称
    client_id = db.Column(db.String(200), nullable=False)
    client_secret = db.Column(db.String(500), nullable=False)
    authorize_url = db.Column(db.String(500), nullable=False)
    token_url = db.Column(db.String(500), nullable=False)
    user_info_url = db.Column(db.String(500), nullable=False)
    jwks_uri = db.Column(db.String(500), nullable=True)  # JWKS端点（用于OIDC）
    scope = db.Column(db.String(200), nullable=False, default='openid email profile')

    # 字段映射配置
    user_id_field = db.Column(db.String(50), default='id')  # 用户ID字段
    email_field = db.Column(db.String(50), default='email')  # 邮箱字段
    name_field = db.Column(db.String(50), default='name')  # 姓名字段
    username_field = db.Column(db.String(50), default='login')  # 用户名字段
    avatar_field = db.Column(db.String(50), default='avatar_url')  # 头像字段

    is_active = db.Column(db.Boolean, default=True)
    auto_register = db.Column(db.Boolean, default=True)  # 自动注册新用户
    skip_2fa = db.Column(db.Boolean, default=True)  # 跳过2FA
    default_role = db.Column(db.String(64), default='Viewer')  # 默认角色

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<OAuthProvider {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'is_active': self.is_active,
            'auto_register': self.auto_register,
            'skip_2fa': self.skip_2fa,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class OAuthAccount(db.Model):
    """用户OAuth账户绑定"""
    __tablename__ = 'oauth_accounts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('oauth_providers.id'), nullable=False)

    # OAuth提供者返回的用户信息
    provider_user_id = db.Column(db.String(200), nullable=False)  # 提供者处的用户ID
    access_token = db.Column(db.Text)  # 访问令牌
    refresh_token = db.Column(db.Text)  # 刷新令牌
    token_expires_at = db.Column(db.DateTime)  # 令牌过期时间

    # 用户信息快照（注册时保存）
    email = db.Column(db.String(64), nullable=False)
    username = db.Column(db.String(64))
    name = db.Column(db.String(64))
    avatar_url = db.Column(db.String(500))

    # 绑定状态
    is_active = db.Column(db.Boolean, default=True)
    last_login_at = db.Column(db.DateTime)
    login_count = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user = db.relationship('User', backref=db.backref('oauth_accounts', lazy='dynamic', cascade='all, delete-orphan'))
    provider = db.relationship('OAuthProvider', backref=db.backref('accounts', lazy='dynamic', cascade='all, delete-orphan'))

    # 唯一约束：同一提供者不能绑定多个相同账户
    __table_args__ = (
        db.UniqueConstraint('provider_id', 'provider_user_id', name='uk_provider_user'),
        db.UniqueConstraint('user_id', 'provider_id', name='uk_user_provider'),
    )

    def __repr__(self):
        return f'<OAuthAccount {self.provider.name}:{self.provider_user_id}>'

    def update_login_stats(self):
        """更新登录统计"""
        self.last_login_at = datetime.utcnow()
        self.login_count += 1
        db.session.add(self)

    def to_dict(self):
        return {
            'id': self.id,
            'provider': self.provider.name,
            'provider_display_name': self.provider.display_name,
            'provider_user_id': self.provider_user_id,
            'email': self.email,
            'username': self.username,
            'name': self.name,
            'avatar_url': self.avatar_url,
            'is_active': self.is_active,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'login_count': self.login_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SSOSession(db.Model):
    """SSO会话管理"""
    __tablename__ = 'sso_sessions'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(128), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    oauth_account_id = db.Column(db.Integer, db.ForeignKey('oauth_accounts.id'), nullable=False)

    # 会话信息
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))

    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    last_accessed_at = db.Column(db.DateTime, default=datetime.utcnow)

    is_active = db.Column(db.Boolean, default=True)

    # 关系
    user = db.relationship('User', backref='sso_sessions')
    oauth_account = db.relationship('OAuthAccount', backref='sso_sessions')

    def __init__(self, **kwargs):
        super(SSOSession, self).__init__(**kwargs)
        if not self.expires_at:
            # 默认24小时过期
            from datetime import timedelta
            self.expires_at = datetime.utcnow() + timedelta(hours=24)

    def is_expired(self):
        """检查会话是否过期"""
        return datetime.utcnow() > self.expires_at

    def is_valid(self):
        """检查会话是否有效"""
        return self.is_active and not self.is_expired()

    def extend_session(self, hours=24):
        """延长会话"""
        from datetime import timedelta
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)
        self.last_accessed_at = datetime.utcnow()
        db.session.add(self)

    def revoke(self):
        """撤销会话"""
        self.is_active = False
        db.session.add(self)

    def __repr__(self):
        return f'<SSOSession {self.session_id[:8]}...>'