#!/usr/bin/env python3
"""
FastGPT API 测试脚本
测试企业 Wiki 系统的 FastGPT API 文件库功能
"""

import requests
import json
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.user import User, Role
from app.models.wiki import Category, Page, Attachment
from app import db

class FastGPTAPITester:
    def __init__(self, base_url='http://localhost:5001'):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_user = None

    def setup_test_data(self):
        """设置测试数据"""
        app = create_app()
        with app.app_context():
            # 创建测试用户
            test_user = User.query.filter_by(username='fastgpt_test').first()
            if not test_user:
                test_user = User(
                    username='fastgpt_test',
                    email='fastgpt@test.com',
                    name='FastGPT Test User',
                    password='test123456'
                )
                db.session.add(test_user)
                db.session.commit()

            # 创建测试分类
            test_category = Category.query.filter_by(name='FastGPT Test Category').first()
            if not test_category:
                test_category = Category(
                    name='FastGPT Test Category',
                    description='Test category for FastGPT API',
                    created_by=test_user.id
                )
                db.session.add(test_category)
                db.session.commit()

            # 创建测试页面
            test_page = Page.query.filter_by(title='FastGPT Test Page').first()
            if not test_page:
                test_page = Page(
                    title='FastGPT Test Page',
                    content='# FastGPT Test Page\n\nThis is a test page for FastGPT API integration.\n\n## Features\n\n- File listing\n- Content retrieval\n- Read URL generation',
                    author_id=test_user.id,
                    category_id=test_category.id,
                    is_public=True,
                    is_published=True
                )
                db.session.add(test_page)
                db.session.commit()

            self.test_user = test_user
            print(f"✓ Test data setup complete")
            print(f"  User: {test_user.username}")
            print(f"  Password: test123456")
            print(f"  Category: {test_category.name}")
            print(f"  Page: {test_page.title}")

    def test_file_list(self):
        """测试文件列表接口"""
        print("\n--- Testing File List API ---")

        # 测试使用密码作为 token
        token = 'test123456'  # 使用密码作为 token
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        # 测试获取根目录文件列表
        response = self.session.post(
            f'{self.base_url}/api/v1/file/list',
            headers=headers,
            json={'parentId': None, 'searchKey': ''}
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✓ File list API test passed")
                print(f"  Found {len(data.get('data', []))} items")
                # 显示几个示例文件名
                items = data.get('data', [])[:3]
                for item in items:
                    print(f"  - {item.get('name', 'Unknown')}")
            else:
                print("✗ File list API test failed:", data.get('message'))
        else:
            print("✗ File list API test failed with status code:", response.status_code)

    def test_file_content(self):
        """测试文件内容接口"""
        print("\n--- Testing File Content API ---")

        token = 'test123456'
        headers = {'Authorization': f'Bearer {token}'}

        # 先获取一个页面ID
        with create_app().app_context():
            test_page = Page.query.filter_by(title='FastGPT Test Page').first()
            if test_page:
                page_id = f'page_{test_page.id}'

                # 测试获取页面内容
                response = self.session.get(
                    f'{self.base_url}/api/v1/file/content',
                    headers=headers,
                    params={'id': page_id}
                )

                print(f"Status Code: {response.status_code}")
                print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        print("✓ File content API test passed")
                        print(f"  Title: {data.get('data', {}).get('title')}")
                        content = data.get('data', {}).get('content', '')[:100]
                        print(f"  Content preview: {content}...")
                    else:
                        print("✗ File content API test failed:", data.get('message'))
                else:
                    print("✗ File content API test failed with status code:", response.status_code)
            else:
                print("✗ Test page not found")

    def test_file_read_url(self):
        """测试文件阅读链接接口"""
        print("\n--- Testing File Read URL API ---")

        token = 'test123456'
        headers = {'Authorization': f'Bearer {token}'}

        # 先获取一个页面ID
        with create_app().app_context():
            test_page = Page.query.filter_by(title='FastGPT Test Page').first()
            if test_page:
                page_id = f'page_{test_page.id}'

                # 测试获取页面阅读链接
                response = self.session.get(
                    f'{self.base_url}/api/v1/file/read',
                    headers=headers,
                    params={'id': page_id}
                )

                print(f"Status Code: {response.status_code}")
                print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        print("✓ File read URL API test passed")
                        print(f"  Read URL: {data.get('data', {}).get('url')}")
                    else:
                        print("✗ File read URL API test failed:", data.get('message'))
                else:
                    print("✗ File read URL API test failed with status code:", response.status_code)
            else:
                print("✗ Test page not found")

    def test_invalid_token(self):
        """测试无效 token"""
        print("\n--- Testing Invalid Token ---")

        headers = {'Authorization': 'Bearer invalid_token'}

        response = self.session.post(
            f'{self.base_url}/api/v1/file/list',
            headers=headers,
            json={'parentId': None, 'searchKey': ''}
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        if response.status_code == 401:
            print("✓ Invalid token test passed - correctly rejected")
        else:
            print("✗ Invalid token test failed - should return 401")

    def run_all_tests(self):
        """运行所有测试"""
        print("=== FastGPT API Integration Test ===")

        try:
            # 设置测试数据
            self.setup_test_data()

            # 运行测试
            self.test_file_list()
            self.test_file_content()
            self.test_file_read_url()
            self.test_invalid_token()

            print("\n=== Test Complete ===")
            print("To use FastGPT API:")
            print("1. baseURL: http://localhost:5001")
            print("2. authorization: Bearer test123456")
            print("3. Or use any existing username/password as token")

        except Exception as e:
            print(f"✗ Test failed with error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    # 检查服务器是否运行
    tester = FastGPTAPITester()

    try:
        response = requests.get(f'{tester.base_url}/', timeout=5)
        if response.status_code == 200:
            print("✓ Server is running")
            tester.run_all_tests()
        else:
            print("✗ Server is not responding correctly")
            print("Please start the Flask server first:")
            print("python run.py")
    except requests.exceptions.RequestException:
        print("✗ Cannot connect to server")
        print("Please start the Flask server first:")
        print("python run.py")
        print(f"Then run this test again from another terminal")