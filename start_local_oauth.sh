#!/bin/bash

# 本地开发环境启动脚本（使用生产域名进行OAuth测试）

echo "=== 启动本地开发环境（UKey OAuth测试） ==="
echo

# 检查hosts文件配置
echo "🔍 检查hosts文件配置..."
if grep -q "wiki.ukey.pw" /etc/hosts 2>/dev/null; then
    echo "   ✅ hosts文件已配置"
else
    echo "   ⚠️ 需要配置hosts文件"
    echo
    echo "📝 请执行以下命令配置hosts文件:"
    echo "   sudo nano /etc/hosts"
    echo "   添加以下行:"
    echo "   127.0.0.1 wiki.ukey.pw"
    echo
    echo "🔧 或者执行一键配置:"
    echo "   sudo sh -c 'echo \"127.0.0.1 wiki.ukey.pw\" >> /etc/hosts'"
    echo
    read -p "是否现在配置hosts文件? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo sh -c 'echo "127.0.0.1 wiki.ukey.pw" >> /etc/hosts'
        echo "   ✅ hosts文件配置完成"
    fi
fi
echo

# 验证OAuth配置
echo "🔐 验证OAuth配置..."
python test_local_oauth.py
if [ $? -ne 0 ]; then
    echo "   ❌ OAuth配置验证失败"
    exit 1
fi
echo

# 设置环境变量
echo "🌍 设置环境变量..."
export FLASK_CONFIG=development
export SERVER_NAME=wiki.ukey.pw
export UKEY_CLIENT_ID=13iq0tuehs65mjw5wg4a3
export UKEY_CLIENT_SECRET=cHIRllg0jOtNHTuWC7q8RNeicTP8trCa

echo "   ✅ 环境变量设置完成"
echo

echo "🚀 启动本地开发服务器..."
echo
echo "📋 访问信息:"
echo "   OAuth登录: https://wiki.ukey.pw/auth/login"
echo "   备用访问: http://127.0.0.1:5001/auth/login"
echo "   应用首页: https://wiki.ukey.pw"
echo
echo "⚠️ 注意事项:"
echo "   1. 确保hosts文件已配置"
echo "   2. 浏览器可能需要清除缓存"
echo "   3. OAuth回调地址: https://wiki.ukey.pw/oauth/callback/ukey"
echo
echo "按 Ctrl+C 停止服务器"
echo

# 启动应用
python run.py