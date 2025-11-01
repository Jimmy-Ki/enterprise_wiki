# UKey企业知识库生产环境部署指南

## 🎯 生产环境信息

- **域名**: `https://wiki.ukey.pw`
- **OAuth提供者**: UKey统一认证
- **回调地址**: `https://wiki.ukey.pw/oauth/callback/ukey`

## ✅ 配置完成状态

### 1. OAuth配置
- ✅ UKey应用配置完成
- ✅ 回调地址已在UKey管理后台注册
- ✅ OAuth服务支持HTTPS生产环境
- ✅ 自动注册和2FA跳过功能已启用

### 2. 数据库配置
- ✅ 数据库表已创建
- ✅ OAuth提供者已配置
- ✅ 默认用户角色已创建

### 3. 应用配置
- ✅ 生产环境配置文件已更新
- ✅ HTTPS强制启用
- ✅ 安全Cookie设置已配置

## 🚀 部署步骤

### 方式一：使用部署脚本（推荐）

```bash
# 1. 给脚本执行权限
chmod +x deploy_production.sh

# 2. 运行部署脚本
./deploy_production.sh
```

### 方式二：手动部署

```bash
# 1. 设置环境变量
export FLASK_CONFIG=production
export SERVER_NAME=wiki.ukey.pw
export UKEY_CLIENT_ID=13iq0tuehs65mjw5wg4a3
export UKEY_CLIENT_SECRET=cHIRllg0jOtNHTuWC7q8RNeicTP8trCa

# 2. 初始化数据库（首次部署）
python init_production.py

# 3. 启动应用
python run.py
```

## 📋 环境变量配置

创建 `.env` 文件或在服务器上设置以下环境变量：

```bash
# 应用配置
FLASK_CONFIG=production
SERVER_NAME=wiki.ukey.pw
SECRET_KEY=your-secret-key-here

# OAuth配置
UKEY_CLIENT_ID=13iq0tuehs65mjw5wg4a3
UKEY_CLIENT_SECRET=cHIRllg0jOtNHTuWC7q8RNeicTP8trCa
UKEY_ISSUER=https://auth.ukey.pw/oidc
UKEY_REDIRECT_URI=https://wiki.ukey.pw/oauth/callback/ukey
UKEY_SCOPE="openid email profile"
UKEY_AUTO_REGISTER=true
UKEY_SKIP_2FA=true
UKEY_DEFAULT_ROLE=Viewer

# 数据库配置
DATABASE_URL=sqlite:///enterprise_wiki.db
```

## 🔗 重要URL

- **应用首页**: `https://wiki.ukey.pw`
- **登录页面**: `https://wiki.ukey.pw/auth/login`
- **OAuth登录**: `https://wiki.ukey.pw/oauth/login/ukey`
- **OAuth回调**: `https://wiki.ukey.pw/oauth/callback/ukey`

## ⚠️ 部署前检查清单

### 服务器配置
- [ ] HTTPS证书已安装并配置
- [ ] 防火墙允许5001端口（或你配置的端口）
- [ ] 域名 `wiki.ukey.pw` 已正确解析到服务器IP
- [ ] 服务器时间已同步

### UKey配置
- [ ] UKey管理后台中回调地址已注册：`https://wiki.ukey.pw/oauth/callback/ukey`
- [ ] 应用状态为"启用"
- [ ] 客户端ID和密钥配置正确

### 应用配置
- [ ] 环境变量已正确设置
- [ ] 数据库文件权限正确
- [ ] 日志目录权限正确

## 🧪 验证部署

### 1. 配置验证脚本
```bash
python verify_production_oauth.py
```

### 2. 手动验证步骤
1. 访问 `https://wiki.ukey.pw/auth/login`
2. 点击"使用UKey统一认证登录"
3. 应该跳转到UKey授权页面
4. 完成授权后自动返回应用
5. 用户自动创建并登录成功

## 🎉 功能特性

### OAuth单点登录
- ✅ 支持UKey统一认证
- ✅ 自动用户注册
- ✅ 用户信息自动同步
- ✅ 账户绑定功能

### 智能安全策略
- ✅ OAuth用户自动跳过2FA验证
- ✅ 传统用户保留2FA验证
- ✅ SSO会话管理
- ✅ 安全的会话配置

### 用户管理
- ✅ 用户资料中的OAuth账户管理
- ✅ 支持多个OAuth账户绑定
- ✅ 账户解绑功能
- ✅ 登录历史记录

## 🔧 故障排除

### 常见问题

#### 1. invalid_redirect_uri错误
- 确保UKey管理后台的回调地址完全匹配：`https://wiki.ukey.pw/oauth/callback/ukey`
- 检查URL中不要有多余的斜杠

#### 2. HTTPS证书问题
- 确保SSL证书有效且已安装
- 检查证书链是否完整

#### 3. 数据库权限问题
- 确保应用进程对数据库文件有读写权限
- 检查数据库文件路径正确

#### 4. 端口访问问题
- 确保防火墙允许配置的端口
- 检查Nginx或其他反向代理配置

### 日志查看
```bash
# 查看应用日志
tail -f app.log

# 查看OAuth相关日志
grep -i "oauth" app.log

# 查看错误日志
grep -i "error" app.log
```

## 📞 技术支持

如果遇到问题，请提供以下信息：
1. 完整的错误信息
2. 当前的访问URL
3. 应用日志
4. 服务器环境信息

---

## 🎯 部署成功！

一旦按照上述步骤完成部署，您的UKey企业知识库将具备完整的单点登录功能！用户可以通过UKey统一认证无缝登录，享受智能的安全策略和便捷的用户体验。