# 工具脚本

本目录包含系统管理和维护相关的工具脚本。

## 文件说明

### 数据管理工具
- `bulk_create_articles.py` - 批量创建Wiki文章的工具
- `bulk_create_users.py` - 批量创建用户的工具

### 系统维护工具
- `fix_circular_db.py` - 修复数据库循环引用问题
- `manage_server.py` - 服务器管理工具

### 安装配置工具
- `setup.py` - 系统安装和配置脚本

## 使用方法

### 批量创建用户
```bash
python3 tools/bulk_create_users.py
```

### 批量创建文章
```bash
python3 tools/bulk_create_articles.py
```

### 修复数据库问题
```bash
python3 tools/fix_circular_db.py
```

### 服务器管理
```bash
python3 tools/manage_server.py
```

### 系统安装
```bash
python3 tools/setup.py
```

## 注意事项

1. 运行这些脚本前请确保已正确配置数据库连接
2. 建议在开发环境中先测试脚本功能
3. 批量操作脚本可能会产生大量数据，请谨慎使用
4. 系统维护脚本建议在系统维护期间运行