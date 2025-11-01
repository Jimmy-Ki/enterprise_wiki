# UKey OAuth单点登录配置指南

## 概述

本指南详细说明如何配置UKey统一认证系统与企业知识库的OAuth单点登录集成。

## 🔐 认证信息

- **应用ID**: `13iq0tuehs65mjw5wg4a3`
- **客户端密钥**: `cHIRllg0jOtNHTuWC7q8RNeicTP8trCa`
- **端点ID**: `https://auth.ukey.pw/oidc`

## 🌐 回调地址配置

### 开发环境
```
http://localhost/oauth/callback/ukey
```

### 生产环境
```
https://yourdomain.com/oauth/callback/ukey
```

## ⚙️ 系统配置

### 1. 环境变量配置

在 `.env` 文件中添加以下配置：

```bash
# UKey OAuth配置
UKEY_CLIENT_ID=13iq0tuehs65mjw5wg4a3
UKEY_CLIENT_SECRET=cHIRllg0jOtNHTuWC7q8RNeicTP8trCa
UKEY_ISSUER=https://auth.ukey.pw/oidc
UKEY_SCOPE=openid email profile
UKEY_AUTO_REGISTER=true
UKEY_SKIP_2FA=true
UKEY_DEFAULT_ROLE=Viewer

# 可选：指定回调地址（如果不设置则自动生成）
# UKEY_REDIRECT_URI=https://yourdomain.com/oauth/callback/ukey
```

### 2. 数据库配置

运行配置脚本自动创建UKey OAuth提供者：

```bash
python configure_ukey_oauth.py
```

或使用Flask命令：

```bash
flask add-oauth-provider \
  --provider ukey \
  --client-id "13iq0tuehs65mjw5wg4a3" \
  --client-secret "cHIRllg0jOtNHTuWC7q8RNeicTP8trCa" \
  --display-name "UKey统一认证" \
  --active \
  --auto-register \
  --skip-2fa \
  --default-role "Viewer"
```

## 🚀 快速部署步骤

### 1. 配置UKey管理后台

1. 登录UKey管理控制台
2. 找到应用ID: `13iq0tuehs65mjw5wg4a3`
3. 配置回调地址：
   - 开发环境: `http://localhost/oauth/callback/ukey`
   - 生产环境: `https://yourdomain.com/oauth/callback/ukey`
4. 确保应用已启用OAuth2.0功能

### 2. 配置知识库系统

```bash
# 1. 安装依赖（如果还没有安装）
pip install authlib>=1.2.0

# 2. 运行数据库迁移
flask db upgrade

# 3. 初始化OAuth提供者
flask init-oauth-providers

# 4. 配置UKey OAuth
python configure_ukey_oauth.py

# 5. 查看配置状态
python -m flask list-oauth-providers
```

### 3. 测试配置

```bash
# 运行测试脚本
python test_ukey_oauth.py

# 启动开发服务器
flask run
```

## 🎯 功能特性

### ✅ 已启用功能

- **自动用户注册**: UKey用户首次登录时自动创建账户
- **跳过双因素认证**: UKey用户无需输入2FA码
- **随机密码生成**: 自动生成安全密码作为备用
- **邮箱验证跳过**: UKey用户自动激活账户
- **账户绑定管理**: 用户可绑定/解绑UKey账户
- **会话管理**: 详细的SSO会话跟踪

### 🔒 安全配置

- **CSRF防护**: 完整的跨站请求伪造防护
- **会话超时**: 24小时自动过期
- **令牌安全**: 安全的访问令牌存储和管理
- **状态验证**: OAuth状态参数验证

## 📋 用户界面

### 登录页面
- 显示"使用UKey统一认证登录"按钮
- 橙色钥匙图标 🗝️
- 与传统登录并存

### 个人资料页面
- 新增"OAuth账户"标签页
- 显示已绑定的UKey账户
- 支持绑定/解绑操作
- SSO会话管理

### 管理员界面
- OAuth提供者管理页面
- 回调地址显示
- 提供者启用/禁用控制

## 🔧 故障排除

### 常见问题

#### 1. 回调地址错误
**症状**: OAuth回调失败，显示"无效的重定向URI"
**解决方案**:
- 检查UKey管理后台的回调地址配置
- 确保与系统生成的回调地址完全一致
- 检查是否包含http/https协议

#### 2. 客户端认证失败
**症状**: "invalid_client" 或认证失败错误
**解决方案**:
- 验证客户端ID和密钥是否正确
- 检查应用是否在UKey中启用
- 确认OAuth2.0功能已开启

#### 3. 用户信息获取失败
**症状**: 登录成功但无法获取用户信息
**解决方案**:
- 检查用户信息端点是否可访问
- 验证权限范围配置
- 确认字段映射正确

#### 4. 自动注册失败
**症状**: UKey登录后无法创建用户账户
**解决方案**:
- 检查数据库连接
- 确认自动注册功能已启用
- 查看应用日志中的错误信息

### 调试方法

#### 1. 查看应用日志
```bash
flask run
# 观察控制台输出的OAuth相关日志
```

#### 2. 检查配置
```bash
python test_ukey_oauth.py
# 运行完整配置测试
```

#### 3. 验证数据库
```python
from app import create_app, db
from app.models.oauth import OAuthProvider

app = create_app('development')
with app.app_context():
    provider = OAuthProvider.query.filter_by(name='ukey').first()
    print(f"Provider: {provider.display_name}")
    print(f"Active: {provider.is_active}")
```

## 🔄 维护操作

### 日常维护

```bash
# 查看OAuth提供者状态
python -m flask list-oauth-providers

# 查看用户OAuth绑定
python -c "
from app import create_app, db
from app.models.oauth import OAuthAccount
app = create_app('development')
with app.app_context():
    accounts = OAuthAccount.query.filter_by(is_active=True).all()
    print(f'Total OAuth accounts: {len(accounts)}')
"

# 重新注册OAuth服务
python -c "
from app import create_app
from app.services.oauth_service import oauth_service
app = create_app('development')
with app.app_context():
    oauth_service._register_providers()
    print('OAuth service re-registered')
"
```

### 紧急操作

```bash
# 禁用UKey OAuth
python -m flask toggle-oauth-provider --provider ukey

# 启用UKey OAuth
python -m flask toggle-oauth-provider --provider ukey

# 重新配置UKey
python configure_ukey_oauth.py
```

## 📊 监控指标

### 关键指标

1. **OAuth登录成功率**
2. **用户注册数量**
3. **会话活跃数量**
4. **错误率统计**

### 日志监控

关注以下日志信息：
- OAuth提供者注册成功/失败
- 用户登录成功/失败
- 令牌刷新操作
- 会话创建/撤销

## 🎨 界面自定义

### UKey图标样式
```css
/* 登录按钮 */
.oauth-btn:hover .fas.fa-key {
    color: #ff6b35;
}

/* 账户管理 */
.oauth-account .fas.fa-key {
    color: #ff6b35;
}
```

### 自定义显示名称
如需修改"UKey统一认证"显示名称，可执行：
```bash
python -c "
from app import create_app, db
from app.models.oauth import OAuthProvider
app = create_app('development')
with app.app_context():
    provider = OAuthProvider.query.filter_by(name='ukey').first()
    provider.display_name = '您的自定义名称'
    db.session.commit()
    print('Display name updated')
"
```

## 📞 技术支持

如遇到问题，请提供以下信息：

1. **错误信息**: 完整的错误日志
2. **配置信息**: OAuth提供者配置状态
3. **环境信息**: 开发/生产环境，域名等
4. **复现步骤**: 详细的操作步骤

---

**配置完成！您的企业知识库现已支持UKey统一认证单点登录。** 🎉

用户现在可以通过UKey账户便捷登录，享受自动注册、跳过2FA等智能化功能。