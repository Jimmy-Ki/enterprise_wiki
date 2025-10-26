#!/usr/bin/env python3
"""
批量创建随机用户的脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Role
import secrets
import string
import random
from datetime import datetime

# 中文姓氏和名字
CHINESE_SURNAMES = [
    "王", "李", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴",
    "徐", "孙", "胡", "朱", "高", "林", "何", "郭", "马", "罗",
    "梁", "宋", "郑", "谢", "韩", "唐", "冯", "于", "董", "萧",
    "程", "曹", "袁", "邓", "许", "傅", "沈", "曾", "彭", "吕"
]

CHINESE_GIVEN_NAMES = [
    "伟", "芳", "娜", "秀英", "敏", "静", "丽", "强", "磊", "军",
    "洋", "勇", "艳", "杰", "娟", "涛", "明", "超", "秀兰", "霞",
    "平", "刚", "桂英", "玉兰", "萍", "建华", "文", "晨", "光", "琳",
    "志", "华", "建国", "红", "小红", "晓东", "春", "梅", "丽丽", "强强"
]

# 英文名字
ENGLISH_FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley"
]

ENGLISH_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
    "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
    "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young"
]

def generate_random_password(length=12):
    """生成随机密码"""
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(characters) for _ in range(length))

def generate_chinese_name():
    """生成中文姓名"""
    surname = random.choice(CHINESE_SURNAMES)
    given_name = random.choice(CHINESE_GIVEN_NAMES)
    if random.random() > 0.7:  # 30%概率两个字的名字
        given_name += random.choice(CHINESE_GIVEN_NAMES)
    return surname + given_name

def generate_english_name():
    """生成英文姓名"""
    first_name = random.choice(ENGLISH_FIRST_NAMES)
    last_name = random.choice(ENGLISH_LAST_NAMES)
    return f"{first_name} {last_name}"

def generate_username(name, email_prefix):
    """生成用户名"""
    # 尝试多种用户名格式
    options = [
        email_prefix,
        f"{email_prefix}{random.randint(1, 999)}",
        f"{name.lower().replace(' ', '.')}{random.randint(1, 99)}",
        f"{name.lower().replace(' ', '_')}{random.randint(1, 99)}",
        f"user{random.randint(1000, 9999)}"
    ]

    # 检查用户名是否已存在
    for username in options:
        if not User.query.filter_by(username=username).first():
            return username

    # 如果都存在，生成完全随机的用户名
    return f"user_{secrets.token_hex(4)}"

def create_random_users(count=20):
    """批量创建随机用户"""
    app = create_app()
    with app.app_context():
        print(f"开始创建 {count} 个随机用户...")

        # 获取所有角色
        roles = Role.query.all()
        if not roles:
            print("错误：数据库中没有角色，请先运行 Role.insert_roles()")
            return

        # 设置角色权重（普通用户更多，管理员更少）
        role_weights = []
        role_names = []
        for role in roles:
            if role.name == 'Administrator':
                weight = 1  # 5% 管理员
            elif role.name == 'Moderator':
                weight = 2  # 10% 版主
            elif role.name == 'Editor':
                weight = 7  # 35% 编辑
            else:  # Viewer
                weight = 10  # 50% 普通用户

            role_weights.extend([role] * weight)
            role_names.append(role.name)

        created_users = []

        for i in range(count):
            try:
                # 随机选择姓名类型（70%中文，30%英文）
                is_chinese = random.random() > 0.3

                if is_chinese:
                    name = generate_chinese_name()
                    # 中文邮箱
                    email_prefix = f"user{i+1:02d}_{secrets.token_hex(2)}"
                    email = f"{email_prefix}@example.com"
                else:
                    name = generate_english_name()
                    # 英文邮箱
                    email_prefix = name.lower().replace(' ', '.')
                    email = f"{email_prefix}.{random.randint(1, 999)}@example.com"

                # 生成唯一用户名
                username = generate_username(name, email_prefix)

                # 生成随机密码
                password = generate_random_password()

                # 随机选择角色
                role = random.choice(role_weights)

                # 随机设置用户状态
                is_active = random.random() > 0.1  # 90% 激活
                confirmed = random.random() > 0.2   # 80% 已确认邮箱

                # 创建用户
                user = User(
                    username=username,
                    email=email,
                    name=name,
                    role_id=role.id,
                    is_active=is_active,
                    confirmed=confirmed
                )

                # 设置密码
                user.password = password

                # 设置随机加入时间（过去30天内）
                days_ago = random.randint(0, 30)
                member_since = datetime.utcnow() - timedelta(days=days_ago)
                user.member_since = member_since
                user.last_seen = member_since

                db.session.add(user)
                created_users.append({
                    'username': username,
                    'email': email,
                    'name': name,
                    'password': password,
                    'role': role.name,
                    'active': is_active,
                    'confirmed': confirmed
                })

                print(f"创建用户 {i+1}/{count}: {username} ({name}) - {role.name}")

            except Exception as e:
                print(f"创建用户 {i+1} 失败: {str(e)}")
                db.session.rollback()
                continue

        try:
            db.session.commit()
            print(f"\n✅ 成功创建 {len(created_users)} 个用户！")

            # 显示统计信息
            role_stats = {}
            active_count = 0
            confirmed_count = 0

            for user_info in created_users:
                role = user_info['role']
                role_stats[role] = role_stats.get(role, 0) + 1
                if user_info['active']:
                    active_count += 1
                if user_info['confirmed']:
                    confirmed_count += 1

            print(f"\n📊 统计信息:")
            print(f"总用户数: {len(created_users)}")
            print(f"激活用户: {active_count} ({active_count/len(created_users)*100:.1f}%)")
            print(f"已确认邮箱: {confirmed_count} ({confirmed_count/len(created_users)*100:.1f}%)")
            print(f"\n📋 角色分布:")
            for role, count in role_stats.items():
                percentage = count/len(created_users)*100
                print(f"  {role}: {count} ({percentage:.1f}%)")

            # 保存用户信息到文件
            with open('created_users.txt', 'w', encoding='utf-8') as f:
                f.write("批量创建的用户信息\n")
                f.write("=" * 50 + "\n")
                f.write(f"创建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"总用户数: {len(created_users)}\n\n")

                for i, user_info in enumerate(created_users, 1):
                    f.write(f"用户 {i}:\n")
                    f.write(f"  用户名: {user_info['username']}\n")
                    f.write(f"  邮箱: {user_info['email']}\n")
                    f.write(f"  姓名: {user_info['name']}\n")
                    f.write(f"  密码: {user_info['password']}\n")
                    f.write(f"  角色: {user_info['role']}\n")
                    f.write(f"  状态: {'激活' if user_info['active'] else '未激活'}\n")
                    f.write(f"  邮箱确认: {'已确认' if user_info['confirmed'] else '未确认'}\n")
                    f.write(f"  登录地址: http://127.0.0.1:5004/auth/login\n")
                    f.write("-" * 30 + "\n")

            print(f"\n💾 用户信息已保存到 created_users.txt 文件")

        except Exception as e:
            print(f"❌ 保存到数据库失败: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    from datetime import timedelta

    # 检查是否提供了用户数量参数
    count = 20
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            print("错误：用户数量必须是整数")
            sys.exit(1)

    create_random_users(count)