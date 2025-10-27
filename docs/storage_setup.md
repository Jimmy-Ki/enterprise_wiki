# 存储服务配置指南

本项目支持多种存储后端，包括本地存储、S3兼容存储（AWS S3、Cloudflare R2、MinIO等）。

## 支持的存储方案

### 1. 本地存储（默认）
- **优点**：简单配置，无需外部服务
- **缺点**：受服务器磁盘空间限制，不适合分布式部署
- **适用场景**：开发环境、小型部署、单机部署

### 2. S3兼容存储
- **AWS S3**：亚马逊云存储服务
- **Cloudflare R2**：Cloudflare的对象存储服务，无出口费用
- **MinIO**：自托管S3兼容存储服务
- **其他S3兼容服务**：任何支持S3 API的存储服务

## 配置方法

### 环境变量配置

#### 本地存储
```bash
# .env 文件
STORAGE_TYPE=local
UPLOAD_FOLDER=app/static/uploads
BASE_URL=/static/uploads
```

#### Cloudflare R2 配置
```bash
# .env 文件
STORAGE_TYPE=s3

# Cloudflare R2 设置
S3_ENDPOINT_URL=https://your-account-id.r2.cloudflarestorage.com
S3_ACCESS_KEY=your-r2-access-key
S3_SECRET_KEY=your-r2-secret-key
S3_BUCKET_NAME=your-bucket-name
S3_REGION=auto
S3_CDN_URL=https://your-custom-domain.com  # 可选：自定义域名CDN
```

#### MinIO 配置
```bash
# .env 文件
STORAGE_TYPE=s3

# MinIO 设置
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=enterprise-wiki
S3_REGION=us-east-1
# S3_CDN_URL=  # 可选：如果有CDN则填写
```

#### AWS S3 配置
```bash
# .env 文件
STORAGE_TYPE=s3

# AWS S3 设置
S3_ENDPOINT_URL=https://s3.amazonaws.com
S3_ACCESS_KEY=your-aws-access-key-id
S3_SECRET_KEY=your-aws-secret-access-key
S3_BUCKET_NAME=your-s3-bucket-name
S3_REGION=us-west-2
S3_CDN_URL=https://your-cloudfront-domain.cloudfront.net  # 可选：CloudFront CDN
```

## 获取配置信息

### Cloudflare R2

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 进入 R2 Object Storage
3. 创建存储桶 (Bucket)
4. 创建 API 令牌：
   - 前往 "Manage R2 API tokens"
   - 创建具有 "Object Read and Write" 权限的令牌
   - 记录 Access Key ID 和 Secret Access Key
5. 账户ID在Dashboard右侧可以找到
6. Endpoint URL 格式：`https://<account-id>.r2.cloudflarestorage.com`

### MinIO

1. 安装 MinIO：
   ```bash
   docker run -p 9000:9000 -p 9001:9001 \
     -e "MINIO_ROOT_USER=minioadmin" \
     -e "MINIO_ROOT_PASSWORD=minioadmin" \
     quay.io/minio/minio server /data --console-address ":9001"
   ```

2. 访问 http://localhost:9001
3. 使用 minioadmin/minioadmin 登录
4. 创建存储桶
5. 生成访问密钥

### AWS S3

1. 登录 AWS Management Console
2. 进入 S3 服务
3. 创建存储桶
4. 创建 IAM 用户并附加 S3 访问策略
5. 生成访问密钥

## 文件组织结构

### 本地存储
```
app/static/uploads/
├── attachments/
│   ├── 20240101_120000_document.pdf
│   ├── 20240101_120500_image.jpg
│   └── ...
├── avatars/
│   ├── 20240101_130000_user1.png
│   └── ...
└── exports/
    └── ...
```

### S3存储
```
s3://your-bucket/
├── attachments/
│   ├── 20240101_120000_document.pdf
│   ├── 20240101_120500_image.jpg
│   └── ...
├── avatars/
│   └── ...
└── exports/
    └── ...
```

## 功能特性

### 安全性
- 文件类型白名单验证
- 文件大小限制（默认16MB）
- 安全文件名处理
- 上传权限控制

### 文件管理
- 自动生成唯一文件名（时间戳前缀）
- 文件元数据存储（大小、类型、上传者等）
- 支持文件夹分类存储
- 文件删除功能

### URL生成
- 自动生成访问URL
- 支持CDN加速
- 本地和远程存储统一接口

## 迁移指南

### 从本地存储迁移到S3存储

1. 备份现有文件和数据库
2. 配置S3存储服务
3. 上传现有文件到S3：
   ```python
   # 迁移脚本示例
   from app.services.storage_service import create_storage_service
   from app.models import Attachment
   from app import create_app, db

   app = create_app()
   with app.app_context():
       s3_service = create_storage_service(app.config['STORAGE_CONFIG'])

       attachments = Attachment.query.all()
       for attachment in attachments:
           if attachment.file_path.startswith('app/static/'):
               # 读取本地文件
               with open(attachment.file_path, 'rb') as f:
                   # 上传到S3
                   result = s3_service.upload_file(
                       file_data=f,
                       filename=attachment.original_filename,
                       content_type=attachment.mime_type,
                       folder='attachments'
                   )
                   if result['success']:
                       # 更新数据库记录
                       attachment.file_path = result['relative_path']
                       db.session.commit()
   ```

### 从S3存储迁移到本地存储

1. 下载S3中的文件到本地
2. 更新环境变量配置
3. 运行数据库更新脚本

## 故障排除

### 常见问题

1. **S3连接失败**
   - 检查访问密钥是否正确
   - 验证存储桶名称是否存在
   - 确认Endpoint URL格式正确

2. **文件上传失败**
   - 检查文件大小是否超限
   - 验证文件类型是否在允许列表中
   - 检查存储空间是否充足

3. **权限问题**
   - 确认S3存储桶权限配置
   - 检查用户是否具有上传权限
   - 验证CORS设置（如使用前端直接上传）

### 日志查看

```python
# 启用调试日志查看上传详细信息
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 性能优化建议

1. **启用CDN加速**：配置CDN URL提高文件访问速度
2. **文件压缩**：对图片等文件进行压缩
3. **分片上传**：大文件考虑分片上传
4. **缓存策略**：设置合适的文件缓存头
5. **定期清理**：定期清理未使用的文件

## 安全建议

1. **访问控制**：设置适当的存储桶访问策略
2. **加密存储**：启用服务端加密
3. **定期备份**：重要文件定期备份
4. **监控审计**：启用访问日志和监控