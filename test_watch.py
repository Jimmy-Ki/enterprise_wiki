#!/usr/bin/env python3
"""
测试 watch 功能的脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Page, Watch, WatchNotification, WatchTargetType, WatchEventType
from app.services.watch_service import WatchService
from flask import current_app

def test_watch_functionality():
    """测试 watch 功能"""
    app = create_app('development')

    with app.app_context():
        print("🚀 开始测试 Watch 功能...")

        # 确保数据库表存在
        db.create_all()

        # 查找现有用户
        user1 = User.query.first()
        if not user1:
            print("❌ 没有找到用户，请先创建用户")
            return False

        print(f"✅ 找到用户: {user1.username}")

        # 查找现有页面
        page = Page.query.first()
        if not page:
            print("❌ 没有找到页面，请先创建页面")
            return False

        print(f"✅ 找到页面: {page.title}")

        # 创建 watch
        print("\n📝 创建 Watch...")
        watch = WatchService.create_watch(
            user_id=user1.id,
            target_type=WatchTargetType.PAGE,
            target_id=page.id,
            events=['page_updated', 'page_deleted']
        )

        if watch:
            print(f"✅ Watch 创建成功，ID: {watch.id}")
        else:
            print("❌ Watch 创建失败")
            return False

        # 测试事件触发
        print("\n🔔 测试事件触发...")

        # 手动触发页面更新事件
        notifications_created = WatchService.trigger_event(
            event_type=WatchEventType.PAGE_UPDATED,
            target_type=WatchTargetType.PAGE,
            target_id=page.id,
            actor_id=user1.id  # 这里用同一个用户，实际中应该是不同用户
        )

        print(f"✅ 触发了 {notifications_created} 个通知")

        # 检查通知
        notifications = WatchService.get_user_notifications(user1.id)
        print(f"✅ 用户 {user1.username} 有 {len(notifications)} 个通知")

        for notification in notifications:
            print(f"   - {notification.title}: {notification.message}")

        # 检查未读数量
        unread_count = WatchService.get_unread_count(user1.id)
        print(f"✅ 未读通知数量: {unread_count}")

        # 测试标记为已读
        if notifications:
            success = WatchService.mark_notification_read(notifications[0].id, user1.id)
            if success:
                print("✅ 通知已标记为已读")
            else:
                print("❌ 标记已读失败")

        print("\n🎉 Watch 功能测试完成！")
        return True

def test_email_configuration():
    """测试邮件配置"""
    app = create_app('development')

    with app.app_context():
        print("\n📧 测试邮件配置...")

        mail_config = {
            'server': current_app.config.get('MAIL_SERVER'),
            'port': current_app.config.get('MAIL_PORT'),
            'use_tls': current_app.config.get('MAIL_USE_TLS'),
            'username': current_app.config.get('MAIL_USERNAME'),
            'sender': current_app.config.get('MAIL_SENDER')
        }

        print("📋 邮件配置:")
        for key, value in mail_config.items():
            if key == 'password':
                print(f"   {key}: {'*' * len(value) if value else 'None'}")
            else:
                print(f"   {key}: {value}")

        if mail_config['server'] and mail_config['username']:
            print("✅ 邮件配置已设置")
            return True
        else:
            print("❌ 邮件配置不完整")
            return False

if __name__ == '__main__':
    print("=" * 50)
    print("🧪 Enterprise Wiki Watch 功能测试")
    print("=" * 50)

    # 测试邮件配置
    email_ok = test_email_configuration()

    # 测试 watch 功能
    watch_ok = test_watch_functionality()

    print("\n" + "=" * 50)
    if email_ok and watch_ok:
        print("🎉 所有测试通过！Watch 功能正常工作")
        sys.exit(0)
    else:
        print("❌ 部分测试失败，请检查配置")
        sys.exit(1)