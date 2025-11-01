#!/usr/bin/env python3
"""
配置UKey OAuth提供者脚本
"""

import os
from app import create_app, db
from app.models.oauth import OAuthProvider
from app.services.oauth_service import oauth_service


def configure_ukey_oauth():
    """配置UKey OAuth提供者"""
    app = create_app('development')

    with app.app_context():
        print("=== 配置UKey OAuth提供者 ===")

        # 从环境变量或直接设置配置
        config = {
            'client_id': os.environ.get('UKEY_CLIENT_ID', '13iq0tuehs65mjw5wg4a3'),
            'client_secret': os.environ.get('UKEY_CLIENT_SECRET', 'cHIRllg0jOtNHTuWC7q8RNeicTP8trCa'),
            'issuer': os.environ.get('UKEY_ISSUER', 'https://auth.ukey.pw/oidc'),
            'auto_register': os.environ.get('UKEY_AUTO_REGISTER', 'true').lower() == 'true',
            'skip_2fa': os.environ.get('UKEY_SKIP_2FA', 'true').lower() == 'true',
            'default_role': os.environ.get('UKEY_DEFAULT_ROLE', 'Viewer')
        }

        # UKey OIDC端点配置
        ukey_config = {
            'name': 'ukey',
            'display_name': 'UKey统一认证',
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'authorize_url': f"{config['issuer']}/auth",
            'token_url': f"{config['issuer']}/token",
            'user_info_url': f"{config['issuer']}/userinfo",
            'scope': 'openid email profile',
            'user_id_field': 'sub',
            'email_field': 'email',
            'name_field': 'name',
            'username_field': 'preferred_username',
            'avatar_field': 'picture',
            'is_active': True,
            'auto_register': config['auto_register'],
            'skip_2fa': config['skip_2fa'],
            'default_role': config['default_role']
        }

        # 检查是否已存在
        existing = OAuthProvider.query.filter_by(name='ukey').first()
        if existing:
            print("更新现有UKey OAuth提供者配置...")
            existing.display_name = ukey_config['display_name']
            existing.client_id = ukey_config['client_id']
            existing.client_secret = ukey_config['client_secret']
            existing.authorize_url = ukey_config['authorize_url']
            existing.token_url = ukey_config['token_url']
            existing.user_info_url = ukey_config['user_info_url']
            existing.scope = ukey_config['scope']
            existing.user_id_field = ukey_config['user_id_field']
            existing.email_field = ukey_config['email_field']
            existing.name_field = ukey_config['name_field']
            existing.username_field = ukey_config['username_field']
            existing.avatar_field = ukey_config['avatar_field']
            existing.is_active = ukey_config['is_active']
            existing.auto_register = ukey_config['auto_register']
            existing.skip_2fa = ukey_config['skip_2fa']
            existing.default_role = ukey_config['default_role']

            print("✅ UKey OAuth提供者配置已更新")
        else:
            print("创建新的UKey OAuth提供者...")
            provider = OAuthProvider(**ukey_config)
            db.session.add(provider)
            print("✅ UKey OAuth提供者已创建")

        db.session.commit()

        # 重新注册OAuth提供者
        try:
            oauth_service._register_providers()
            print("✅ OAuth服务已重新注册")
        except Exception as e:
            print(f"⚠️ OAuth服务重新注册失败: {e}")

        # 输出配置信息
        print("\n=== 配置信息 ===")
        print(f"提供者名称: {ukey_config['name']}")
        print(f"显示名称: {ukey_config['display_name']}")
        print(f"客户端ID: {ukey_config['client_id']}")
        print(f"授权端点: {ukey_config['authorize_url']}")
        print(f"令牌端点: {ukey_config['token_url']}")
        print(f"用户信息端点: {ukey_config['user_info_url']}")
        print(f"自动注册: {ukey_config['auto_register']}")
        print(f"跳过2FA: {ukey_config['skip_2fa']}")
        print(f"默认角色: {ukey_config['default_role']}")
        print(f"状态: {'启用' if ukey_config['is_active'] else '禁用'}")

        return ukey_config


def get_callback_urls():
    """获取回调地址列表"""
    app = create_app('development')

    with app.app_context():
        from flask import url_for
        with app.test_request_context():
            callback_urls = []
            providers = OAuthProvider.query.all()
            for provider in providers:
                callback_url = url_for('oauth.callback', provider_name=provider.name, _external=True)
                callback_urls.append({
                    'provider': provider.name,
                    'display_name': provider.display_name,
                    'callback_url': callback_url
                })

            return callback_urls


def create_env_file():
    """创建.env文件模板"""
    env_content = """# UKey OAuth配置
UKEY_CLIENT_ID=13iq0tuehs65mjw5wg4a3
UKEY_CLIENT_SECRET=cHIRllg0jOtNHTuWC7q8RNeicTP8trCa
UKEY_ISSUER=https://auth.ukey.pw/oidc
UKEY_SCOPE=openid email profile
UKEY_AUTO_REGISTER=true
UKEY_SKIP_2FA=true
UKEY_DEFAULT_ROLE=Viewer

# 可选：指定回调地址（如果不设置则自动生成）
# UKEY_REDIRECT_URI=https://yourdomain.com/oauth/callback/ukey
"""

    with open('.env.ukey', 'w', encoding='utf-8') as f:
        f.write(env_content)

    print("✅ 已创建 .env.ukey 文件")
    print("请将此文件内容添加到您的 .env 文件中")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == 'configure':
            configure_ukey_oauth()
        elif command == 'callbacks':
            print("=== OAuth回调地址 ===")
            urls = get_callback_urls()
            for url_info in urls:
                print(f"{url_info['display_name']} ({url_info['provider']}):")
                print(f"  {url_info['callback_url']}")
                print()
        elif command == 'env':
            create_env_file()
        else:
            print("可用命令:")
            print("  configure  - 配置UKey OAuth提供者")
            print("  callbacks  - 显示所有回调地址")
            print("  env        - 创建.env文件模板")
    else:
        # 默认执行配置
        configure_ukey_oauth()

        print("\n=== 回调地址 ===")
        urls = get_callback_urls()
        for url_info in urls:
            if url_info['provider'] == 'ukey':
                print(f"UKey OAuth回调地址:")
                print(f"  {url_info['callback_url']}")
                break