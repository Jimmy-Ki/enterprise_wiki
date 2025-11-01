# OAuth单点登录(SSO)功能使用指南

## 功能概述

本系统现已支持OAuth单点登录功能，具有以下特性：

### 核心功能
- ✅ **多平台OAuth支持**: 支持Google、GitHub、Microsoft等主流OAuth提供者
- ✅ **自动用户注册**: OAuth用户自动注册，无需手动创建账号
- ✅ **智能2FA策略**: OAuth用户可跳过2FA验证，传统用户保留2FA
- ✅ **账户绑定管理**: 用户可以绑定/解绑多个OAuth账户
- ✅ **会话管理**: 详细的SSO会话跟踪和管理
- ✅ **安全机制**: 完整的CSRF防护和会话管理

### 安全特性
- 🔒 **随机密码生成**: OAuth用户自动获得强随机密码
- 🔒 **邮箱验证跳过**: OAuth用户自动激活，无需邮箱验证
- 🔒 **会话超时**: SSO会话自动过期，可手动撤销
- 🔒 **账户隔离**: OAuth账户与本地账户独立管理

## 系统架构

### 数据库表结构

1. **oauth_providers** - OAuth提供者配置
2. **oauth_accounts** - 用户OAuth账户绑定
3. **sso_sessions** - SSO会话管理

### 关键组件

- **OAuthService**: 核心OAuth服务类
- **OAuth控制器**: 处理登录/回调/管理
- **用户模型扩展**: OAuth相关方法和属性
- **模板集成**: 登录页面和个人资料页面

## 安装和配置

### 1. 依赖安装

```bash
pip install authlib>=1.2.0
```

### 2. 数据库迁移

```bash
flask db upgrade
```

### 3. 初始化OAuth提供者

```bash
# 初始化默认提供者配置
flask init-oauth-providers

# 查看所有提供者
flask list-oauth-providers
```

### 4. 配置OAuth提供者

以Google为例：

```bash
flask add-oauth-provider \
  --provider google \
  --client-id "your-google-client-id" \
  --client-secret "your-google-client-secret" \
  --display-name "Google" \
  --active \
  --auto-register \
  --skip-2fa \
  --default-role "Viewer"
```

## 使用指南

### 管理员配置

#### 1. 获取OAuth凭据

**Google OAuth 2.0:**
1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目或选择现有项目
3. 启用 Google+ API
4. 创建OAuth 2.0客户端ID
5. 设置回调URL: `http://yourdomain.com/oauth/callback/google`

**GitHub OAuth:**
1. 访问 [GitHub Developer Settings](https://github.com/settings/developers)
2. 创建新的OAuth App
3. 设置回调URL: `http://yourdomain.com/oauth/callback/github`

**Microsoft Azure:**
1. 访问 [Azure Portal](https://portal.azure.com/)
2. 创建应用注册
3. 设置回调URL: `http://yourdomain.com/oauth/callback/microsoft`

#### 2. 配置提供者

```bash
# 启用Google OAuth
flask add-oauth-provider \
  --provider google \
  --client-id "your-client-id" \
  --client-secret "your-client-secret" \
  --active

# 启用GitHub OAuth
flask add-oauth-provider \
  --provider github \
  --client-id "your-client-id" \
  --client-secret "your-client-secret" \
  --active

# 查看状态
flask list-oauth-providers
```

#### 3. 管理提供者

```bash
# 禁用提供者
flask toggle-oauth-provider --provider google

# 启用提供者
flask toggle-oauth-provider --provider google
```

### 用户使用

#### 1. OAuth登录

1. 访问登录页面
2. 选择OAuth提供者按钮（Google、GitHub等）
3. 重定向到提供者授权页面
4. 授权后自动返回并登录

#### 2. 账户管理

1. 登录后访问个人资料页面
2. 点击"OAuth账户"标签页
3. 查看已绑定的账户
4. 绑定新账户或解绑现有账户

#### 3. 会话管理

1. 在OAuth账户管理页面
2. 点击"查看会话"
3. 查看所有活跃的SSO会话
4. 可手动撤销异常会话

## 高级配置

### 环境变量配置

```bash
# 可选：设置管理员邮箱
export ADMIN_EMAIL="admin@company.com"

# 可选：配置重定向域名
export OAUTH_REDIRECT_DOMAIN="https://yourdomain.com"
```

### 自定义配置

#### 1. 添加新的OAuth提供者

编辑 `app/services/oauth_service.py` 的 `initialize_default_providers` 方法：

```python
{
    'name': 'custom_provider',
    'display_name': 'Custom Provider',
    'client_id': 'placeholder-client-id',
    'client_secret': 'placeholder-client-secret',
    'authorize_url': 'https://auth.example.com/oauth/authorize',
    'token_url': 'https://auth.example.com/oauth/token',
    'user_info_url': 'https://auth.example.com/oauth/userinfo',
    'scope': 'openid email profile',
    'user_id_field': 'id',
    'email_field': 'email',
    'name_field': 'name',
    'username_field': 'username',
    'avatar_field': 'avatar_url',
    'is_active': False
}
```

#### 2. 自定义用户权限

修改提供者的 `default_role` 参数：

```bash
flask add-oauth-provider \
  --provider google \
  --client-id "..." \
  --client-secret "..." \
  --default-role "Editor"  # 设置为编辑者
```

## 故障排除

### 常见问题

#### 1. OAuth回调失败
- 检查回调URL配置是否正确
- 确认OAuth应用的重定向URI设置
- 检查客户端ID和密钥是否正确

#### 2. 用户注册失败
- 检查提供者是否启用了 `auto_register`
- 确认用户信息字段映射正确
- 检查数据库连接

#### 3. 2FA跳过不生效
- 确认提供者启用了 `skip_2fa`
- 检查用户是否通过OAuth创建
- 验证OAuth账户绑定状态

### 调试方法

#### 1. 查看日志

```bash
# 启动应用并查看日志
flask run
```

#### 2. 测试OAuth配置

```bash
# 运行测试脚本
python test_oauth_setup.py

# 创建演示提供者
python test_oauth_setup.py demo
```

#### 3. 检查数据库

```python
from app import create_app, db
from app.models.oauth import OAuthProvider, OAuthAccount

app = create_app('development')
with app.app_context():
    # 查看提供者
    providers = OAuthProvider.query.all()
    for p in providers:
        print(f"{p.name}: {p.is_active}")

    # 查看账户绑定
    accounts = OAuthAccount.query.all()
    print(f"Total OAuth accounts: {len(accounts)}")
```

## 安全建议

### 1. 生产环境配置

- 使用HTTPS协议
- 设置安全的回调URL
- 定期轮换客户端密钥
- 启用会话超时

### 2. 监控和审计

- 监控OAuth登录活动
- 定期检查异常会话
- 记录账户绑定/解绑操作
- 审查用户权限变更

### 3. 用户教育

- 告知用户OAuth登录的安全性
- 指导用户管理OAuth账户
- 提醒用户定期检查会话
- 建议使用强密码作为备用

## API参考

### OAuth控制器端点

- `GET /oauth/login/<provider_name>` - OAuth登录入口
- `GET /oauth/callback/<provider_name>` - OAuth回调处理
- `GET /oauth/link/<provider_name>` - 绑定OAuth账户
- `POST /oauth/unlink/<provider_name>` - 解绑OAuth账户
- `GET /oauth/manage_accounts` - 管理OAuth账户
- `GET /oauth/sso_sessions` - SSO会话管理

### 命令行工具

- `flask add-oauth-provider` - 添加OAuth提供者
- `flask list-oauth-providers` - 列出OAuth提供者
- `flask toggle-oauth-provider` - 启用/禁用提供者
- `flask init-oauth-providers` - 初始化默认提供者

### 数据模型

#### OAuthProvider
- `name`: 提供者名称
- `display_name`: 显示名称
- `client_id`: 客户端ID
- `client_secret`: 客户端密钥
- `is_active`: 是否启用
- `auto_register`: 是否自动注册
- `skip_2fa`: 是否跳过2FA

#### OAuthAccount
- `user_id`: 用户ID
- `provider_id`: 提供者ID
- `provider_user_id`: 提供者用户ID
- `access_token`: 访问令牌
- `refresh_token`: 刷新令牌
- `is_active`: 是否激活

#### SSOSession
- `user_id`: 用户ID
- `oauth_account_id`: OAuth账户ID
- `session_id`: 会话ID
- `ip_address`: IP地址
- `expires_at`: 过期时间
- `is_active`: 是否活跃

## 更新日志

### v1.0.0 (2025-11-01)
- ✅ 完整的OAuth SSO功能实现
- ✅ 支持Google、GitHub、Microsoft
- ✅ 智能双因素认证策略
- ✅ 用户账户绑定管理
- ✅ SSO会话管理
- ✅ 安全机制和防护
- ✅ 管理员工具和CLI
- ✅ 用户界面集成

---

如有问题或建议，请查看代码注释或联系开发团队。