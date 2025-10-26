# 测试脚本

本目录包含系统的所有测试脚本。

## 文件说明

- `test_fastgpt_api.py` - FastGPT API集成测试脚本
  - 测试文件列表接口 `/api/v1/file/list`
  - 测试文件内容接口 `/api/v1/file/content`
  - 测试文件阅读链接接口 `/api/v1/file/read`
  - 测试无效token的认证失败情况

## 使用方法

```bash
# 确保Flask服务器正在运行
python3 run.py

# 在另一个终端运行测试
python3 tests/test_fastgpt_api.py
```

## 测试环境

- 测试用户: `fastgpt_test`
- 测试密码: `test123456`
- 测试页面: `FastGPT Test Page`
- 测试分类: `FastGPT Test Category`