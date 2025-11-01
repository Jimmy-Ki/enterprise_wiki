"""OAuth服务类，处理OAuth认证流程"""
import secrets
import requests
from datetime import datetime, timedelta
from flask import current_app, url_for, request, session
from authlib.integrations.flask_client import OAuth
from app import db
from app.models import User
from app.models.oauth import OAuthProvider, OAuthAccount, SSOSession


class OAuthService:
    def __init__(self, app=None):
        self.oauth = OAuth(app)
        if app:
            self.init_app(app)

    def init_app(self, app):
        """初始化OAuth服务"""
        self.oauth = OAuth(app)
        # 不要在初始化时立即注册提供者，等数据库创建后再注册

    def _register_providers(self):
        """注册所有活跃的OAuth提供者"""
        try:
            providers = OAuthProvider.query.filter_by(is_active=True).all()
            current_app.logger.info(f"Found {len(providers)} active OAuth providers")

            for provider in providers:
                self._register_provider(provider)

        except Exception as e:
            current_app.logger.error(f"Error in _register_providers: {str(e)}")
            # 不抛出异常，允许应用继续运行

    def get_provider(self, provider_name):
        """获取OAuth提供者"""
        try:
            provider = OAuthProvider.query.filter_by(name=provider_name, is_active=True).first()
            if not provider:
                current_app.logger.error(f"OAuth provider '{provider_name}' not found or inactive")
                return None

            # 确保OAuth客户端已注册
            if provider_name not in self.oauth._registry:
                current_app.logger.info(f"Registering OAuth client for provider: {provider_name}")
                self._register_provider(provider)

            return provider
        except Exception as e:
            current_app.logger.error(f"Error getting OAuth provider '{provider_name}': {str(e)}")
            return None

    def _register_provider(self, provider):
        """注册单个OAuth提供者"""
        try:
            # 使用数据库中的JWKS URI（如果有）
            jwks_uri = provider.jwks_uri

            # 如果数据库中没有JWKS URI，但提供了OIDC端点，则尝试构建JWKS URI
            if not jwks_uri and provider.name == 'ukey':
                # 从授权URL构建正确的JWKS端点
                base_url = provider.authorize_url.rsplit('/auth', 1)[0]
                jwks_uri = f"{base_url}/jwks"

            self.oauth.register(
                name=provider.name,
                client_id=provider.client_id,
                client_secret=provider.client_secret,
                server_metadata_url=None,
                client_kwargs={
                    'scope': provider.scope
                },
                authorize_url=provider.authorize_url,
                authorize_params=None,
                access_token_url=provider.token_url,
                access_token_params=None,
                userinfo_endpoint=provider.user_info_url,
                userinfo_method='GET',
                userinfo_kwargs=None,
                jwks_uri=jwks_uri,
                client_auth_method='client_secret_post'
            )
            current_app.logger.info(f"Successfully registered OAuth provider: {provider.name}")
            if jwks_uri:
                current_app.logger.info(f"Using JWKS URI: {jwks_uri}")
        except Exception as e:
            current_app.logger.error(f"Failed to register OAuth provider {provider.name}: {str(e)}")
            raise

    def get_authorization_url(self, provider_name, redirect_uri=None):
        """获取授权URL"""
        from flask import session, url_for

        provider = self.get_provider(provider_name)
        if not provider:
            raise ValueError(f"OAuth provider {provider_name} not found or inactive")

        # 确保OAuth客户端已注册
        if provider_name not in self.oauth._registry:
            self._register_provider(provider)

        client = self.oauth.create_client(provider_name)
        if not client:
            raise ValueError(f"OAuth client for {provider_name} not configured")

        # 生成state参数防止CSRF攻击
        state = secrets.token_urlsafe(32)
        try:
            session['oauth_state'] = state
            session['oauth_provider'] = provider_name
        except RuntimeError:
            # 如果没有session上下文，使用应用上下文
            pass

        # 构建回调URL
        if not redirect_uri:
            try:
                redirect_uri = url_for('oauth.callback', provider_name=provider_name, _external=True)
                # 替换localhost为实际的服务器名称
                # 处理HTTPS环境
                if current_app.config.get('FORCE_HTTPS') or current_app.config.get('PREFERRED_URL_SCHEME') == 'https':
                    redirect_uri = redirect_uri.replace('http://', 'https://')
                server_name = current_app.config.get('SERVER_NAME', '127.0.0.1')
                redirect_uri = redirect_uri.replace('localhost', server_name)
            except RuntimeError:
                # 如果没有request上下文，使用默认值
                server_name = current_app.config.get('SERVER_NAME', '127.0.0.1')
                redirect_uri = f"http://{server_name}:5000/oauth/callback/{provider_name}"

        # 获取授权URL
        try:
            auth_url = client.authorize_redirect(redirect_uri, state=state)
            return auth_url
        except Exception as e:
            current_app.logger.error(f"Error generating authorization URL: {str(e)}")
            # 手动构建授权URL作为备用方案
            params = {
                'client_id': provider.client_id,
                'redirect_uri': redirect_uri,
                'response_type': 'code',
                'scope': provider.scope,
                'state': state
            }
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            return f"{provider.authorize_url}?{query_string}"

    def handle_callback(self, provider_name, code=None, state=None, error=None):
        """处理OAuth回调"""
        # 验证state参数
        if state != session.get('oauth_state'):
            raise ValueError("Invalid state parameter")

        provider = self.get_provider(provider_name)
        if not provider:
            raise ValueError(f"OAuth provider {provider_name} not found")

        if error:
            raise ValueError(f"OAuth error: {error}")

        client = self.oauth.create_client(provider_name)
        if not client:
            raise ValueError(f"OAuth client for {provider_name} not configured")

        # 获取访问令牌（让authlib自动处理redirect_uri）
        token = client.authorize_access_token()

        # 获取用户信息
        user_info = client.userinfo()

        return self._process_oauth_login(provider, user_info, token)

    def _process_oauth_login(self, provider, user_info, token):
        """处理OAuth登录逻辑"""
        try:
            # 提取用户信息
            provider_user_id = str(user_info.get(provider.user_id_field, ''))
            email = user_info.get(provider.email_field, '').lower().strip()
            username = user_info.get(provider.username_field) or user_info.get('login', '')
            name = user_info.get(provider.name_field, username)
            avatar_url = user_info.get(provider.avatar_field, '')

            if not email:
                raise ValueError("OAuth provider did not return email address")

            # 检查是否已经存在OAuth账户绑定
            oauth_account = OAuthAccount.query.filter_by(
                provider_id=provider.id,
                provider_user_id=provider_user_id,
                is_active=True
            ).first()

            if oauth_account:
                # 已有绑定，直接登录
                user = oauth_account.user
                self._update_oauth_account(oauth_account, token, user_info)
                return self._create_user_session(user, oauth_account)
            else:
                # 检查是否有用户已使用该邮箱注册
                user = User.query.filter_by(email=email).first()

                if user:
                    # 用户已存在，绑定OAuth账户
                    oauth_account = self._create_oauth_account(
                        user, provider, provider_user_id, token, user_info
                    )
                    return self._create_user_session(user, oauth_account)
                else:
                    # 新用户，创建账户
                    if not provider.auto_register:
                        raise ValueError("Auto-registration is disabled for this provider")

                    user = self._create_new_user(provider, user_info)
                    oauth_account = self._create_oauth_account(
                        user, provider, provider_user_id, token, user_info
                    )
                    return self._create_user_session(user, oauth_account)

        except Exception as e:
            current_app.logger.error(f"Error processing OAuth login: {str(e)}")
            raise

    def _update_oauth_account(self, oauth_account, token, user_info):
        """更新OAuth账户信息"""
        oauth_account.access_token = token.get('access_token')
        oauth_account.refresh_token = token.get('refresh_token')

        # 设置令牌过期时间
        expires_in = token.get('expires_in')
        if expires_in:
            oauth_account.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        oauth_account.update_login_stats()
        db.session.add(oauth_account)
        db.session.flush()  # 确保更新被立即保存

    def _create_oauth_account(self, user, provider, provider_user_id, token, user_info):
        """创建OAuth账户绑定"""
        oauth_account = OAuthAccount(
            user_id=user.id,
            provider_id=provider.id,
            provider_user_id=provider_user_id,
            access_token=token.get('access_token'),
            refresh_token=token.get('refresh_token'),
            email=user_info.get(provider.email_field),
            username=user_info.get(provider.username_field) or user_info.get('login'),
            name=user_info.get(provider.name_field),
            avatar_url=user_info.get(provider.avatar_field),
            is_active=True,
            login_count=1,
            last_login_at=datetime.utcnow()
        )

        # 设置令牌过期时间
        expires_in = token.get('expires_in')
        if expires_in:
            oauth_account.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        db.session.add(oauth_account)
        db.session.flush()  # 确保获取到ID但不提交整个事务
        return oauth_account

    def _create_new_user(self, provider, user_info):
        """创建新用户"""
        # 构建用户信息字典
        user_data = {
            'email': user_info.get(provider.email_field),
            'username': user_info.get(provider.username_field) or user_info.get('login'),
            'name': user_info.get(provider.name_field),
            'avatar_url': user_info.get(provider.avatar_field)
        }

        user = User.create_from_oauth(user_data, provider, auto_confirm=True)
        db.session.add(user)
        db.session.flush()  # 确保获取到用户ID但不提交整个事务
        return user

    def _create_user_session(self, user, oauth_account):
        """创建SSO会话"""
        session_id = secrets.token_urlsafe(64)

        sso_session = SSOSession(
            session_id=session_id,
            user_id=user.id,
            oauth_account_id=oauth_account.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:500]
        )

        db.session.add(sso_session)
        db.session.commit()

        return {
            'user': user,
            'oauth_account': oauth_account,
            'sso_session_id': session_id,
            'skip_2fa': oauth_account.provider.skip_2fa
        }

    def get_user_from_sso_session(self, session_id):
        """从SSO会话获取用户"""
        sso_session = SSOSession.query.filter_by(
            session_id=session_id,
            is_active=True
        ).first()

        if not sso_session or not sso_session.is_valid():
            return None

        # 延长会话
        sso_session.extend_session()
        db.session.add(sso_session)

        return sso_session.user

    def revoke_sso_session(self, session_id):
        """撤销SSO会话"""
        sso_session = SSOSession.query.filter_by(session_id=session_id).first()
        if sso_session:
            sso_session.revoke()
            db.session.add(sso_session)
            return True
        return False

    def refresh_access_token(self, oauth_account):
        """刷新访问令牌"""
        if not oauth_account.refresh_token:
            return False

        try:
            client = self.oauth.create_client(oauth_account.provider.name)
            if not client:
                return False

            token = client.refresh_token(
                oauth_account.provider.token_url,
                refresh_token=oauth_account.refresh_token
            )

            oauth_account.access_token = token.get('access_token')
            oauth_account.refresh_token = token.get('refresh_token', oauth_account.refresh_token)

            expires_in = token.get('expires_in')
            if expires_in:
                oauth_account.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            db.session.add(oauth_account)
            return True

        except Exception as e:
            current_app.logger.error(f"Failed to refresh access token: {str(e)}")
            return False

    @staticmethod
    def initialize_default_providers():
        """初始化默认的OAuth提供者配置"""
        default_providers = [
            {
                'name': 'google',
                'display_name': 'Google',
                'client_id': 'placeholder-client-id',
                'client_secret': 'placeholder-client-secret',
                'authorize_url': 'https://accounts.google.com/o/oauth2/v2/auth',
                'token_url': 'https://oauth2.googleapis.com/token',
                'user_info_url': 'https://www.googleapis.com/oauth2/v2/userinfo',
                'scope': 'openid email profile',
                'user_id_field': 'id',
                'email_field': 'email',
                'name_field': 'name',
                'username_field': 'email',
                'avatar_field': 'picture',
                'is_active': False  # 默认禁用，需要配置凭据
            },
            {
                'name': 'github',
                'display_name': 'GitHub',
                'client_id': 'placeholder-client-id',
                'client_secret': 'placeholder-client-secret',
                'authorize_url': 'https://github.com/login/oauth/authorize',
                'token_url': 'https://github.com/login/oauth/access_token',
                'user_info_url': 'https://api.github.com/user',
                'scope': 'user:email',
                'user_id_field': 'id',
                'email_field': 'email',
                'name_field': 'name',
                'username_field': 'login',
                'avatar_field': 'avatar_url',
                'is_active': False  # 默认禁用，需要配置凭据
            },
            {
                'name': 'microsoft',
                'display_name': 'Microsoft',
                'client_id': 'placeholder-client-id',
                'client_secret': 'placeholder-client-secret',
                'authorize_url': 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
                'token_url': 'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                'user_info_url': 'https://graph.microsoft.com/v1.0/me',
                'scope': 'openid email profile',
                'user_id_field': 'id',
                'email_field': 'mail',
                'name_field': 'displayName',
                'username_field': 'userPrincipalName',
                'avatar_field': None,
                'is_active': False  # 默认禁用，需要配置凭据
            },
            {
                'name': 'ukey',
                'display_name': 'UKey统一认证',
                'client_id': 'placeholder-client-id',
                'client_secret': 'placeholder-client-secret',
                'authorize_url': 'https://auth.ukey.pw/oidc/auth',
                'token_url': 'https://auth.ukey.pw/oidc/token',
                'user_info_url': 'https://auth.ukey.pw/oidc/userinfo',
                'scope': 'openid email profile',
                'user_id_field': 'sub',
                'email_field': 'email',
                'name_field': 'name',
                'username_field': 'preferred_username',
                'avatar_field': 'picture',
                'is_active': False  # 默认禁用，需要配置凭据
            }
        ]

        for provider_data in default_providers:
            existing = OAuthProvider.query.filter_by(name=provider_data['name']).first()
            if not existing:
                provider = OAuthProvider(**provider_data)
                db.session.add(provider)
                current_app.logger.info(f"Created default OAuth provider: {provider_data['name']}")

        db.session.commit()


# 全局OAuth服务实例
oauth_service = OAuthService()