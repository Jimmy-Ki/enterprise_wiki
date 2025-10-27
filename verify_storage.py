#!/usr/bin/env python3
"""
快速验证Cloudflare R2存储配置
"""

import os
from dotenv import load_dotenv
load_dotenv()

def verify_config():
    print("🔍 验证存储配置...")
    print(f"存储类型: {os.environ.get('STORAGE_TYPE')}")
    print(f"Endpoint: {os.environ.get('S3_ENDPOINT_URL')}")
    print(f"存储桶: {os.environ.get('S3_BUCKET_NAME')}")
    print(f"CDN URL: {os.environ.get('S3_CDN_URL')}")

    required_vars = ['STORAGE_TYPE', 'S3_ENDPOINT_URL', 'S3_ACCESS_KEY', 'S3_SECRET_KEY', 'S3_BUCKET_NAME']
    missing = [var for var in required_vars if not os.environ.get(var)]

    if missing:
        print(f"❌ 缺少配置: {missing}")
        return False

    print("✅ 配置完整")
    return True

if __name__ == "__main__":
    if verify_config():
        print("🎉 Cloudflare R2配置就绪！")
    else:
        print("❌ 配置不完整，请检查.env文件")