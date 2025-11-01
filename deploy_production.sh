#!/bin/bash

# UKey企业知识库生产环境部署脚本
# 用于 https://wiki.ukey.pw/ 域名

echo "=== UKey企业知识库生产环境部署 ==="
echo

# 设置生产环境变量
export FLASK_CONFIG=production
export SERVER_NAME=wiki.ukey.pw
export PREFERRED_URL_SCHEME=https
export FORCE_HTTPS=true

# OAuth配置
export UKEY_CLIENT_ID=13iq0tuehs65mjw5wg4a3
export UKEY_CLIENT_SECRET=cHIRllg0jOtNHTuWC7q8RNeicTP8trCa
export UKEY_ISSUER=https://auth.ukey.pw/oidc
export UKEY_REDIRECT_URI=https://wiki.ukey.pw/oauth/callback/ukey
export UKEY_SCOPE="openid email profile"
export UKEY_AUTO_REGISTER=true
export UKEY_SKIP_2FA=true
export UKEY_DEFAULT_ROLE=Viewer

# 数据库配置（根据实际部署环境调整）
export DATABASE_URL=sqlite:///enterprise_wiki.db

# 安全配置
export SECRET_KEY=${SECRET_KEY:-"$(openssl rand -hex 32)"}

# 其他配置
export PORT=5001

echo "📋 生产环境配置:"
echo "   域名: $SERVER_NAME"
echo "   协议: $PREFERRED_URL_SCHEME"
echo "   强制HTTPS: $FORCE_HTTPS"
echo "   OAuth回调地址: $UKEY_REDIRECT_URI"
echo "   数据库: $DATABASE_URL"
echo

echo "🔧 初始化应用..."
# 确保数据库存在并初始化
if [ ! -f "enterprise_wiki.db" ]; then
    echo "   创建数据库..."
    python -c "from app import create_app, db; app = create_app('production'); app.app_context().push(); db.create_all(); print('数据库创建完成')"
fi

# 初始化OAuth提供者
echo "   初始化OAuth提供者..."
python -c "
from app import create_app, db
from app.services.oauth_service import oauth_service
from app.models.oauth import OAuthProvider

app = create_app('production')
app.config['SERVER_NAME'] = 'wiki.ukey.pw'

with app.app_context():
    # 检查UKey提供者是否存在
    ukey_provider = OAuthProvider.query.filter_by(name='ukey').first()
    if not ukey_provider:
        print('   创建UKey OAuth提供者...')
        ukey_provider = OAuthProvider(
            name='ukey',
            display_name='UKey统一认证',
            client_id='13iq0tuehs65mjw5wg4a3',
            client_secret='cHIRllg0jOtNHTuWC7q8RNeicTP8trCa',
            authorize_url='https://auth.ukey.pw/oidc/auth',
            token_url='https://auth.ukey.pw/oidc/token',
            user_info_url='https://auth.ukey.pw/oidc/userinfo',
            scope='openid email profile',
            user_id_field='sub',
            email_field='email',
            name_field='name',
            username_field='preferred_username',
            avatar_field='picture',
            is_active=True,
            auto_register=True,
            skip_2fa=True,
            default_role='Viewer'
        )
        db.session.add(ukey_provider)
        db.session.commit()
        print('   ✅ UKey OAuth提供者创建完成')
    else:
        print('   ✅ UKey OAuth提供者已存在')
"

echo
echo "🚀 启动生产环境应用..."
echo "   访问地址: https://wiki.ukey.pw"
echo "   登录页面: https://wiki.ukey.pw/auth/login"
echo
echo "⚠️ 注意事项:"
echo "   1. 确保HTTPS证书已配置"
echo "   2. 确保防火墙允许5001端口"
echo "   3. 确保域名wiki.ukey.pw指向本服务器"
echo "   4. UKey回调地址已配置为: $UKEY_REDIRECT_URI"
echo

# 启动应用
python run.py