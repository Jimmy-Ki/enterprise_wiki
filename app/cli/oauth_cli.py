"""OAuth命令行工具"""
import click
from flask import current_app
from app import db
from app.models.oauth import OAuthProvider
from app.services.oauth_service import oauth_service


@click.command()
@click.option('--provider', required=True, help='Provider name (google, github, microsoft)')
@click.option('--client-id', required=True, help='OAuth client ID')
@click.option('--client-secret', required=True, help='OAuth client secret')
@click.option('--display-name', help='Display name for the provider')
@click.option('--active/--inactive', default=True, help='Enable/disable the provider')
@click.option('--auto-register/--no-auto-register', default=True, help='Auto-register new users')
@click.option('--skip-2fa/--require-2fa', default=True, help='Skip 2FA for OAuth users')
@click.option('--default-role', default='Viewer', help='Default role for new users')
def add_oauth_provider(provider, client_id, client_secret, display_name, active, auto_register, skip_2fa, default_role):
    """添加OAuth提供者"""

    # 检查提供者是否已存在
    existing = OAuthProvider.query.filter_by(name=provider).first()
    if existing:
        click.echo(f'OAuth提供者 {provider} 已存在')
        return

    # 获取默认配置
    default_configs = {
        'google': {
            'display_name': 'Google',
            'authorize_url': 'https://accounts.google.com/o/oauth2/v2/auth',
            'token_url': 'https://oauth2.googleapis.com/token',
            'user_info_url': 'https://www.googleapis.com/oauth2/v2/userinfo',
            'scope': 'openid email profile',
            'user_id_field': 'id',
            'email_field': 'email',
            'name_field': 'name',
            'username_field': 'email',
            'avatar_field': 'picture'
        },
        'github': {
            'display_name': 'GitHub',
            'authorize_url': 'https://github.com/login/oauth/authorize',
            'token_url': 'https://github.com/login/oauth/access_token',
            'user_info_url': 'https://api.github.com/user',
            'scope': 'user:email',
            'user_id_field': 'id',
            'email_field': 'email',
            'name_field': 'name',
            'username_field': 'login',
            'avatar_field': 'avatar_url'
        },
        'microsoft': {
            'display_name': 'Microsoft',
            'authorize_url': 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
            'token_url': 'https://login.microsoftonline.com/common/oauth2/v2.0/token',
            'user_info_url': 'https://graph.microsoft.com/v1.0/me',
            'scope': 'openid email profile',
            'user_id_field': 'id',
            'email_field': 'mail',
            'name_field': 'displayName',
            'username_field': 'userPrincipalName',
            'avatar_field': None
        }
    }

    if provider not in default_configs:
        click.echo(f'不支持的提供者: {provider}')
        return

    config = default_configs[provider]

    # 创建OAuth提供者
    oauth_provider = OAuthProvider(
        name=provider,
        display_name=display_name or config['display_name'],
        client_id=client_id,
        client_secret=client_secret,
        authorize_url=config['authorize_url'],
        token_url=config['token_url'],
        user_info_url=config['user_info_url'],
        scope=config['scope'],
        user_id_field=config['user_id_field'],
        email_field=config['email_field'],
        name_field=config['name_field'],
        username_field=config['username_field'],
        avatar_field=config['avatar_field'],
        is_active=active,
        auto_register=auto_register,
        skip_2fa=skip_2fa,
        default_role=default_role
    )

    db.session.add(oauth_provider)
    db.session.commit()

    click.echo(f'OAuth提供者 {provider} 添加成功')

    # 重新注册OAuth提供者
    try:
        oauth_service._register_providers()
        click.echo('OAuth提供者已重新注册')
    except Exception as e:
        click.echo(f'重新注册OAuth提供者失败: {e}')


@click.command()
def list_oauth_providers():
    """列出所有OAuth提供者"""
    providers = OAuthProvider.query.all()

    if not providers:
        click.echo('没有配置OAuth提供者')
        return

    click.echo('OAuth提供者列表:')
    click.echo('-' * 80)
    click.echo(f'{"名称":<15} {"显示名称":<15} {"状态":<8} {"自动注册":<8} {"跳过2FA":<8}')
    click.echo('-' * 80)

    for provider in providers:
        status = '启用' if provider.is_active else '禁用'
        auto_reg = '是' if provider.auto_register else '否'
        skip_2fa = '是' if provider.skip_2fa else '否'

        click.echo(f'{provider.name:<15} {provider.display_name:<15} {status:<8} {auto_reg:<8} {skip_2fa:<8}')


@click.command()
@click.option('--provider', required=True, help='Provider name to toggle')
def toggle_oauth_provider(provider):
    """启用/禁用OAuth提供者"""
    oauth_provider = OAuthProvider.query.filter_by(name=provider).first()

    if not oauth_provider:
        click.echo(f'OAuth提供者 {provider} 不存在')
        return

    oauth_provider.is_active = not oauth_provider.is_active
    db.session.commit()

    status = '启用' if oauth_provider.is_active else '禁用'
    click.echo(f'OAuth提供者 {provider} 已{status}')

    # 重新注册OAuth提供者
    try:
        oauth_service._register_providers()
        click.echo('OAuth提供者已重新注册')
    except Exception as e:
        click.echo(f'重新注册OAuth提供者失败: {e}')


@click.command()
def init_default_providers():
    """初始化默认OAuth提供者（不包含凭据）"""
    try:
        from app.services.oauth_service import OAuthService
        OAuthService.initialize_default_providers()
        click.echo('默认OAuth提供者已初始化（需要配置客户端凭据）')
    except Exception as e:
        click.echo(f'初始化失败: {e}')


def register_commands(app):
    """注册OAuth命令"""
    app.cli.add_command(add_oauth_provider, name='add-oauth-provider')
    app.cli.add_command(list_oauth_providers, name='list-oauth-providers')
    app.cli.add_command(toggle_oauth_provider, name='toggle-oauth-provider')
    app.cli.add_command(init_default_providers, name='init-oauth-providers')