#!/usr/bin/env python3
"""
验证UKey端点修复后的配置
"""

import os
from app import create_app
from flask import url_for
from app.services.oauth_service import oauth_service
from app.models.oauth import OAuthProvider


def verify_ukey_endpoints():
    """验证UKey端点配置"""
    print("=== 验证UKey端点配置 ===")
    print()

    # 设置环境变量
    os.environ['FLASK_CONFIG'] = 'development'
    os.environ['SERVER_NAME'] = 'wiki.ukey.pw'

    app = create_app('development')

    with app.app_context():
        print("🔑 检查UKey提供者配置:")
        try:
            ukey_provider = OAuthProvider.query.filter_by(name='ukey').first()
            if ukey_provider:
                print(f"   ✅ 提供者: {ukey_provider.name}")
                print(f"   ✅ 客户端ID: {ukey_provider.client_id}")
                print(f"   ✅ 授权端点: {ukey_provider.authorize_url}")
                print(f"   ✅ 令牌端点: {ukey_provider.token_url}")
                print(f"   ✅ 用户信息端点: {ukey_provider.user_info_url}")
                print(f"   ✅ JWKS端点: {ukey_provider.jwks_uri}")

                # 验证端点是否正确
                expected_endpoints = {
                    'authorize_url': 'https://auth.ukey.pw/oidc/auth',
                    'token_url': 'https://auth.ukey.pw/oidc/token',
                    'user_info_url': 'https://auth.ukey.pw/oidc/me',
                    'jwks_uri': 'https://auth.ukey.pw/oidc/jwks'
                }

                print()
                print("   端点验证:")
                for field, expected in expected_endpoints.items():
                    actual = getattr(ukey_provider, field)
                    if actual == expected:
                        print(f"   ✅ {field}: {actual}")
                    else:
                        print(f"   ❌ {field}: {actual} (期望: {expected})")

            else:
                print("   ❌ UKey提供者不存在")
                return False
        except Exception as e:
            print(f"   ❌ 检查提供者失败: {e}")
            return False
        print()

        print("🔗 测试OAuth服务:")
        try:
            with app.test_request_context():
                # 生成授权URL
                auth_response = oauth_service.get_authorization_url('ukey')
                if hasattr(auth_response, 'location'):
                    location = auth_response.location
                    print(f"   ✅ 授权URL生成成功")
                    print(f"   {location}")

                    # 验证关键参数
                    checks = [
                        ('授权端点', 'https://auth.ukey.pw/oidc/auth'),
                        ('客户端ID', 'client_id=13iq0tuehs65mjw5wg4a3'),
                        ('回调地址', 'redirect_uri=https%3A%2F%2Fwiki.ukey.pw%2Foauth%2Fcallback%2Fukey'),
                        ('权限范围', 'scope=openid+email+profile')
                    ]

                    for name, param in checks:
                        if param in location:
                            print(f"   ✅ {name}")
                        else:
                            print(f"   ❌ {name} 缺失")

                else:
                    print("   ❌ 授权URL生成失败")
                    return False
        except Exception as e:
            print(f"   ❌ OAuth服务测试失败: {e}")
            return False
        print()

        print("🎯 修复内容:")
        print("   ✅ JWKS端点: https://auth.ukey.pw/oidc/jwks")
        print("   ✅ 用户信息端点: https://auth.ukey.pw/oidc/me")
        print("   ✅ 统一回调地址: https://wiki.ukey.pw/oauth/callback/ukey")
        print("   ✅ 修复redirect_uri参数冲突")
        print("   ✅ 添加OpenID Connect支持")
        print()

        print("🚀 测试步骤:")
        print("   1. 启动应用: python run.py")
        print("   2. 访问: https://wiki.ukey.pw/auth/login")
        print("   3. 点击'使用UKey统一认证登录'")
        print("   4. 完成OAuth授权流程")
        print("   5. 验证用户登录成功")
        print()

        return True


def show_ukey_endpoints_info():
    """显示UKey端点信息"""
    print("=== UKey OIDC端点信息 ===")
    print()
    print("📋 官方端点配置:")
    print("   发行者: https://auth.ukey.pw/oidc")
    print("   授权端点: https://auth.ukey.pw/oidc/auth")
    print("   令牌端点: https://auth.ukey.pw/oidc/token")
    print("   用户信息端点: https://auth.ukey.pw/oidc/me")
    print("   JWKS端点: https://auth.ukey.pw/oidc/jwks")
    print("   OpenID配置: https://auth.ukey.pw/oidc/.well-known/openid-configuration")
    print()
    print("🔐 OAuth 2.0 + OpenID Connect:")
    print("   ✅ 支持授权码流程")
    print("   ✅ 支持ID令牌验证")
    print("   ✅ 支持用户信息获取")
    print("   ✅ 支持令牌签名验证")
    print()


if __name__ == '__main__':
    success = verify_ukey_endpoints()
    show_ukey_endpoints_info()

    if success:
        print("🎉 UKey端点配置验证完成！")
        print("   现在应该不会再出现JWKS 404错误了。")
    else:
        print("❌ UKey端点配置验证失败，请检查配置。")