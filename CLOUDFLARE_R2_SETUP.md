# Cloudflare R2 存储配置完成

✅ **配置状态**: 已完成并测试通过

## 📋 配置信息

- **Endpoint**: `https://d6351223f25a973eb4483061717a5ab5.r2.cloudflarestorage.com`
- **存储桶**: `wiki`
- **CDN域名**: `https://wiki.jimmyki.com`
- **区域**: `auto`
- **访问状态**: ✅ 已验证

## 🔧 配置文件位置

配置已写入: `.env` 文件
```bash
STORAGE_TYPE=s3
S3_ENDPOINT_URL=https://d6351223f25a973eb4483061717a5ab5.r2.cloudflarestorage.com
S3_ACCESS_KEY=b633f6f8921fff64173ddda837b54326
S3_SECRET_KEY=d78bac83cad90f73cfaca57b1e1e364e7d4f72008703edfd37577ca972cef6cf
S3_BUCKET_NAME=wiki
S3_REGION=auto
S3_CDN_URL=https://wiki.jimmyki.com
```

## 🚀 使用方法

### 1. 启动应用
```bash
python run.py
```

### 2. 上传文件
现在所有文件上传将自动使用 Cloudflare R2 存储：
- 文件将被上传到 `https://d6351223f25a973eb4483061717a5ab5.r2.cloudflarestorage.com/wiki/`
- 访问URL将使用CDN域名: `https://wiki.jimmyki.com/`

### 3. 文件组织结构
```
wiki/
├── attachments/          # 附件文件
│   ├── 20240101_120000_document.pdf
│   └── 20240101_120500_image.jpg
├── avatars/             # 用户头像
├── exports/             # 导出文件
└── temp/                # 临时文件
```

## 🔒 安全提示

1. **保护密钥**: 确保 `.env` 文件不被提交到版本控制系统
2. **权限管理**: 定期检查和更新访问密钥
3. **备份**: 建议定期备份存储桶中的重要文件

## 📊 监控和管理

### Cloudflare R2 Dashboard
1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 进入 R2 Object Storage
3. 查看存储使用情况、访问统计等

### 查看存储内容
```python
from app.services.storage_service import create_storage_service
from app import create_app

app = create_app()
with app.app_context():
    storage = create_storage_service(app.config['STORAGE_CONFIG'])
    # 可以通过 storage.backend.s3_client 进行S3操作
```

## 🛠️ 故障排除

### 常见问题
1. **上传失败**: 检查存储桶权限和访问密钥
2. **CDN访问失败**: 确认CDN域名已正确配置指向R2
3. **403错误**: 检查CORS设置和访问权限

### 测试连接
运行测试脚本验证配置：
```bash
python3 simple_storage_test.py
```

## 📈 优化建议

1. **CORS配置**: 在R2存储桶中配置适当的CORS规则
2. **缓存策略**: 为不同类型文件设置合适的缓存头
3. **压缩**: 对图片等文件进行压缩以节省存储空间
4. **生命周期管理**: 设置自动删除过期的临时文件

## 🔄 迁移现有文件

如果需要从本地存储迁移到R2：

1. 备份现有文件
2. 运行迁移脚本（参考 `docs/storage_setup.md` 中的迁移指南）
3. 验证文件完整性

---

**✨ 配置完成！现在你的企业Wiki将使用高性能的Cloudflare R2存储服务。**