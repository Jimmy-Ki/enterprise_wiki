# UKey OAuth回调地址修复总结

## 🚨 问题状态：需要UKey管理后台配置

### 错误信息
```
{"code":"oidc.invalid_redirect_uri","message":"`redirect_uri` did not match any of the client's registered `redirect_uris`.","error":"invalid_redirect_uri"}
```

## ✅ 已完成的修复

### 1. 代码修复
- ✅ 修正了服务器名称配置（使用127.0.0.1而不是localhost）
- ✅ 更新了OAuth服务的回调URL生成逻辑
- ✅ 确保回调地址与实际访问地址一致

### 2. 当前配置
```
应用服务器: http://127.0.0.1:5001
OAuth登录: http://127.0.0.1:5001/oauth/login/ukey
OAuth回调: http://127.0.0.1:5001/oauth/callback/ukey
```

## 🔧 需要您完成的配置

### 在UKey管理后台添加回调地址

#### 第1步：登录UKey管理控制台
- 访问您的UKey管理系统
- 使用管理员账号登录

#### 第2步：找到您的OAuth应用
- **应用ID**: `13iq0tuehs65mjw5wg4a3`
- **客户端密钥**: `cHIRllg0jOtNHTuWC7q8RNeicTP8trCa`
- **应用名称**: 企业知识库（或您的应用名称）

#### 第3步：配置回调地址
在UKey管理后台的OAuth设置中添加以下回调地址：
```
http://127.0.0.1:5001/oauth/callback/ukey
```

**重要提示**：
- ✅ 使用 `http://` 而不是 `https://`
- ✅ 使用 `127.0.0.1` 而不是 `localhost`
- ✅ 端口号是 `5001`
- ✅ 路径是 `/oauth/callback/ukey`
- ✅ 不要有多余的斜杠

#### 第4步：保存并测试
- 保存配置
- UKey配置通常立即生效
- 重新尝试OAuth登录

## 📋 验证步骤

### 1. 配置验证
```bash
python quick_oauth_test.py
```
应该看到：
```
✅ 授权URL生成成功
✅ 客户端ID正确
```

### 2. 启动应用测试
```bash
python run.py
```
访问：`http://127.0.0.1:5001/auth/login`

### 3. 测试OAuth登录
1. 点击"使用UKey统一认证登录"
2. 应该正常跳转到UKey授权页面
3. 如果UKey后台配置正确，会显示授权界面
4. 授权后自动返回应用并登录

## 🔍 配置验证脚本

### 快速测试脚本
```bash
# 运行配置测试
python quick_oauth_test.py

# 查看当前URL配置
python quick_oauth_test.py urls
```

### 手动验证URL
```python
from app import create_app
app = create_app('development')
app.config['SERVER_NAME'] = '127.0.0.1'

with app.app_context():
    from flask import url_for
    callback_url = url_for('oauth.callback', provider_name='ukey', _external=True)
    print(f"回调地址: {callback_url}")
```

## 🎯 预期结果

### 配置成功后
```
✅ 正常跳转到UKey授权页面
✅ UKey显示授权界面
✅ 授权后自动返回应用
✅ 用户自动创建/登录账户
✅ 跳过2FA验证
```

### 用户登录流程
1. 用户点击"使用UKey统一认证登录"
2. 跳转到：`https://auth.ukey.pw/oidc/auth?...`
3. 用户在UKey页面完成授权
4. 自动返回：`http://127.0.0.1:5001/oauth/callback/ukey`
5. 系统处理回调并创建/登录用户
6. 用户成功登录到企业知识库

## 📁 相关文件

### 修改的文件
- `app/services/oauth_service.py` - 修复回调URL生成逻辑
- `app/config/config.py` - 添加服务器名称配置
- `run.py` - 设置服务器名称

### 测试文件
- `quick_oauth_test.py` - 快速配置测试
- `test_complete_oauth.py` - 完整功能测试

### 配置文档
- `UKey_Redirect_URI_Setup_Guide.md` - 详细配置指南
- `OAuth_Issue_Fixed_Report.md` - 问题修复报告

## 🔧 故障排除

### 如果仍然收到invalid_redirect_uri错误

1. **检查回调地址格式**
   ```
   ✅ http://127.0.0.1:5001/oauth/callback/ukey
   ❌ http://localhost:5001/oauth/callback/ukey
   ❌ https://127.0.0.1:5001/oauth/callback/ukey
   ```

2. **检查UKey配置**
   - 确认在UKey管理后台添加了回调地址
   - 确认保存了配置
   - 确认应用状态为"启用"

3. **检查应用端口**
   ```bash
   python run.py
   # 查看启动端口
   ```

4. **检查网络连接**
   - 确保可以访问UKey OAuth端点
   - 检查防火墙设置

## 📞 技术支持

### 如果需要帮助
1. 提供UKey管理后台的截图
2. 显示完整的错误信息
3. 提供当前访问的URL

### 日志检查
```bash
# 启动应用查看详细日志
python run.py

# 查看OAuth相关日志
grep -i "oauth" app.log
```

---

## 🎯 下一步操作

**请在UKey管理后台添加回调地址后，重新测试OAuth登录功能！**

1. 登录UKey管理控制台
2. 找到应用ID：`13iq0tuehs5mjw5wg4a3`
3. 添加回调地址：`http://127.0.0.1:5001/oauth/callback/ukey`
4. 保存配置
5. 测试OAuth登录

配置完成后，您的UKey单点登录功能将完全正常工作！🚀