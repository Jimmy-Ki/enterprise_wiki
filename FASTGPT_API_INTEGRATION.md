# FastGPT API 文件库集成文档

## 概述

本企业 Wiki 系统已成功集成 FastGPT API 文件库功能，允许 FastGPT 通过标准 API 接口访问 Wiki 中的页面、分类和附件内容。

## API 配置

### 基本信息
- **Base URL**: `http://localhost:5001` (或您的实际部署地址)
- **认证方式**: Bearer Token
- **Token**: 使用任何用户的密码作为 token

### 在 FastGPT 中配置

1. 创建知识库时选择 "API 文件库" 类型
2. 配置以下参数：
   - **baseURL**: `http://localhost:5001`
   - **authorization**: `Bearer test123456` (或其他用户的密码)

## API 接口

### 1. 获取文件树

**接口**: `POST /api/v1/file/list`

**请求示例**:
```bash
curl --location --request POST 'http://localhost:5001/api/v1/file/list' \
--header 'Authorization: Bearer test123456' \
--header 'Content-Type: application/json' \
--data-raw '{
    "parentId": null,
    "searchKey": ""
}'
```

**响应格式**:
```json
{
    "code": 200,
    "success": true,
    "message": "",
    "data": [
        {
            "id": "category_6",
            "parentId": null,
            "name": "FastGPT Test Category",
            "type": "folder",
            "updateTime": "2025-10-25T04:32:55.721541",
            "createTime": "2025-10-25T04:32:55.721541"
        },
        {
            "id": "page_8",
            "parentId": "category_6",
            "name": "FastGPT Test Page",
            "type": "file",
            "updateTime": "2025-10-25T04:32:55.739457",
            "createTime": "2025-10-25T04:32:55.741225"
        }
    ]
}
```

### 2. 获取文件内容

**接口**: `GET /api/v1/file/content?id={file_id}`

**请求示例**:
```bash
curl --location --request GET 'http://localhost:5001/api/v1/file/content?id=page_8' \
--header 'Authorization: Bearer test123456'
```

**响应格式**:
```json
{
    "code": 200,
    "success": true,
    "message": "",
    "data": {
        "title": "FastGPT Test Page",
        "content": "# FastGPT Test Page\n\nThis is a test page for FastGPT API integration.\n\n## Features\n\n- File listing\n- Content retrieval\n- Read URL generation",
        "previewUrl": null
    }
}
```

### 3. 获取文件阅读链接

**接口**: `GET /api/v1/file/read?id={file_id}`

**请求示例**:
```bash
curl --location --request GET 'http://localhost:5001/api/v1/file/read?id=page_8' \
--header 'Authorization: Bearer test123456'
```

**响应格式**:
```json
{
    "code": 200,
    "success": true,
    "message": "",
    "data": {
        "url": "/wiki/8"
    }
}
```

## 文件 ID 格式

系统中不同类型的文件使用以下 ID 格式：

- **页面**: `page_{id}` (例如: `page_8`)
- **附件**: `attachment_{id}` (例如: `attachment_1`)

## 文件名格式

根据要求，API 只返回文件（不返回文件夹），文件名格式为：

**页面文件**: `{分类路径}-{页面标题}.md`

- 分类路径中的层级用连字符 `-` 分隔
- 例如：`FastGPT Test Category-FastGPT Test Page.md`
- 例如：`江梦琦-江梦琦简介.md`
- 例如：`测试分类-Test Article.md`

**附件文件**: 保持原始文件名

- 例如：`document.pdf`
- 例如：`image.png`

## 权限控制

- API 只能访问用户有权限查看的内容
- 公开页面和分类可以直接访问
- 私有内容需要使用对应权限用户的 token
- 管理员可以访问所有内容

## 认证说明

根据您的需求，API 使用用户的密码作为 Bearer token：

1. **使用测试用户**:
   - Token: `test123456`
   - 可以访问测试数据

2. **使用现有用户**:
   - Token: 该用户的密码
   - 只能访问该用户有权限的内容

3. **推荐做法**:
   - 创建专门的 API 用户
   - 为该用户分配适当的权限
   - 使用该用户的密码作为 token

## 错误处理

API 返回标准的 HTTP 状态码：

- `200`: 成功
- `401`: 认证失败（token 无效）
- `403`: 权限不足
- `404`: 资源不存在
- `500`: 服务器内部错误

错误响应格式：
```json
{
    "code": 401,
    "success": false,
    "message": "Invalid token",
    "data": null
}
```

## 功能特性

### 支持的内容类型
- ✅ 页面内容（Markdown 格式，自动转换为纯文本）
- ✅ 扁平化文件列表（只返回文件，不返回文件夹）
- ✅ 分类路径转换为文件名（使用连字符分隔）
- ✅ 附件文件（提供下载链接）
- ✅ 搜索功能（支持标题和内容搜索）

### 权限特性
- ✅ 基于用户权限的访问控制
- ✅ 公开/私有内容区分
- ✅ 基于角色的权限管理

### 安全特性
- ✅ Token 认证
- ✅ CSRF 保护豁免
- ✅ 输入验证和清理
- ✅ 错误日志记录

## 测试

运行测试脚本验证 API 功能：

```bash
source venv/bin/activate
python3 test_fastgpt_api.py
```

## 故障排除

### 常见问题

1. **401 认证失败**
   - 检查 token 是否正确（应该是用户的密码）
   - 确认用户账户是否激活

2. **403 权限不足**
   - 检查用户是否有权限访问指定内容
   - 尝试使用管理员账户的 token

3. **空数据返回**
   - 确认数据库中有相应的页面和分类
   - 检查内容是否设置为公开

### 日志查看

服务器日志会显示详细的错误信息，便于调试。

## 扩展功能

可以根据需要扩展以下功能：

- 批量文件操作
- 文件版本历史
- 更细粒度的权限控制
- 文件元数据扩展
- 缓存机制优化

---

**注意**: 在生产环境中部署时，请确保：
1. 使用 HTTPS 协议
2. 配置合适的防火墙规则
3. 定期更新认证 token
4. 监控 API 调用情况