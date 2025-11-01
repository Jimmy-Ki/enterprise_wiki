# UKey OAuth统一配置指南

## 🎯 配置目标

统一本地开发环境和生产环境的OAuth回调地址，解决 `invalid_redirect_uri` 错误。

## 🔗 统一回调地址

**本地环境和生产环境都使用：**
```
https://wiki.ukey.pw/oauth/callback/ukey
```

## ✅ 配置完成状态

### 1. UKey管理后台配置
- ✅ 回调地址已注册：`https://wiki.ukey.pw/oauth/callback/ukey`
- ✅ 应用状态：启用
- ✅ 应用ID：`13iq0tuehs65mjw5wg4a3`

### 2. 生产环境配置
- ✅ 域名：`https://wiki.ukey.pw`
- ✅ 强制HTTPS：启用
- ✅ 回调地址：`https://wiki.ukey.pw/oauth/callback/ukey`

### 3. 本地开发环境配置
- ✅ 服务器名称：`wiki.ukey.pw`
- ✅ 强制HTTPS：启用
- ✅ 回调地址：`https://wiki.ukey.pw/oauth/callback/ukey`

## 🚀 启动方式

### 本地开发（推荐）

```bash
# 方式一：使用一键启动脚本
./start_local_oauth.sh

# 方式二：手动启动
python run.py
```

### 生产环境部署

```bash
# 使用部署脚本
./deploy_production.sh
```

## 📋 本地开发hosts配置

为了在本地使用生产域名，需要配置hosts文件：

### macOS/Linux
```bash
sudo nano /etc/hosts
# 添加：
127.0.0.1 wiki.ukey.pw
```

### Windows
```
以管理员身份记事本打开：C:\Windows\System32\drivers\etc\hosts
添加：
127.0.0.1 wiki.ukey.pw
```

## 🔗 重要URL

| 环境 | 登录入口 | 回调地址 |
|------|----------|----------|
| 本地开发 | `https://wiki.ukey.pw/auth/login` | `https://wiki.ukey.pw/oauth/callback/ukey` |
| 生产环境 | `https://wiki.ukey.pw/auth/login` | `https://wiki.ukey.pw/oauth/callback/ukey` |

## 🧪 配置验证

### 本地环境验证
```bash
python test_local_oauth.py
```

### 生产环境验证
```bash
python verify_production_oauth.py
```

## ⚙️ 环境配置

### 本地开发环境
```bash
FLASK_CONFIG=development
SERVER_NAME=wiki.ukey.pw
UKEY_CLIENT_ID=13iq0tuehs65mjw5wg4a3
UKEY_CLIENT_SECRET=cHIRllg0jOtNHTuWC7q8RNeicTP8trCa
```

### 生产环境
```bash
FLASK_CONFIG=production
SERVER_NAME=wiki.ukey.pw
UKEY_CLIENT_ID=13iq0tuehs65mjw5wg4a3
UKEY_CLIENT_SECRET=cHIRllg0jOtNHTuWC7q8RNeicTP8trCa
```

## 🎉 OAuth功能特性

### ✅ 已实现功能
- UKey单点登录
- 自动用户注册
- 智能安全策略（OAuth用户跳过2FA）
- 用户账户绑定/解绑
- SSO会话管理
- 统一的登录界面

### 🔐 安全配置
- HTTPS强制启用
- 安全Cookie设置
- CSRF保护
- 会话管理

## 🛠️ 故障排除

### 常见问题及解决方案

#### 1. invalid_redirect_uri 错误
**解决方案：**
- 确保UKey管理后台的回调地址为：`https://wiki.ukey.pw/oauth/callback/ukey`
- 本地开发时确保hosts文件已配置
- 清除浏览器缓存

#### 2. 本地无法访问 https://wiki.ukey.pw
**解决方案：**
- 配置hosts文件：`127.0.0.1 wiki.ukey.pw`
- 或者直接使用IP访问：`http://127.0.0.1:5001/auth/login`

#### 3. 证书警告（本地开发）
**解决方案：**
- 本地开发时浏览器会显示SSL证书警告，这是正常的
- 选择"继续访问"或"高级" -> "继续前往网站"

#### 4. OAuth服务初始化失败
**解决方案：**
- 确保数据库表已创建：运行 `python init_production.py`
- 检查OAuth提供者配置是否正确

## 📞 技术支持

如果遇到问题，请提供：
1. 完整的错误信息
2. 当前访问的URL
3. 浏览器控制台错误
4. 应用日志

---

## 🎯 配置完成！

现在您的本地开发环境和生产环境都使用统一的OAuth回调地址 `https://wiki.ukey.pw/oauth/callback/ukey`，不会再出现 `invalid_redirect_uri` 错误。

### 🚀 立即开始

```bash
# 启动本地开发环境
./start_local_oauth.sh

# 访问登录页面
https://wiki.ukey.pw/auth/login
```

享受无缝的UKey单点登录体验！🎉