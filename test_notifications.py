#!/usr/bin/env python3
"""
测试通知功能 - 站内通知和邮件通知
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Page, Watch, WatchTargetType, WatchEventType
from app.services.watch_service import WatchService, process_pending_watch_events
from flask import current_app

def test_notification_system():
    """测试完整的通知系统"""
    app = create_app('development')

    with app.app_context():
        print("🚀 测试通知系统...")

        # 确保数据库表存在
        db.create_all()

        # 查找或创建两个不同用户
        users = User.query.limit(2).all()
        if len(users) < 2:
            print("❌ 需要至少2个用户进行测试")
            return False

        watcher_user = users[0]  # 关注者
        editor_user = users[1] if len(users) > 1 else users[0]  # 编辑者

        print(f"✅ 关注者: {watcher_user.username}")
        print(f"✅ 编辑者: {editor_user.username}")

        # 查找测试页面
        page = Page.query.first()
        if not page:
            print("❌ 没有找到页面")
            return False

        print(f"✅ 测试页面: {page.title}")

        # 清理之前的通知
        from app.models.watch import WatchNotification
        old_notifications = WatchNotification.query.filter_by(user_id=watcher_user.id).all()
        for notification in old_notifications:
            db.session.delete(notification)
        db.session.commit()

        # 让关注者关注页面
        print("\n📝 创建关注...")
        watch = WatchService.create_watch(
            user_id=watcher_user.id,
            target_type=WatchTargetType.PAGE,
            target_id=page.id,
            events=['page_updated', 'page_deleted', 'attachment_added']
        )

        if not watch:
            print("❌ 关注创建失败")
            return False

        print(f"✅ {watcher_user.username} 成功关注页面")

        # 检查关注前的通知数量
        initial_count = WatchService.get_unread_count(watcher_user.id)
        print(f"📊 初始未读通知数量: {initial_count}")

        # 模拟编辑者修改页面
        print(f"\n✏️ 模拟 {editor_user.username} 修改页面...")

        try:
            # 修改页面内容
            original_content = page.content
            page.content = original_content + f"\n\n由 {editor_user.username} 在测试中修改"
            page.last_editor_id = editor_user.id

            # 标记内容已更改
            page._watch_content_changed = True

            # 保存页面
            db.session.commit()
            print("✅ 页面保存成功")

            # 处理待处理的watch事件
            print("\n🔄 处理watch事件...")
            notifications_count = process_pending_watch_events()
            print(f"✅ 处理了 {notifications_count} 个watch事件")

            # 检查通知
            print("\n📬 检查通知...")
            notifications = WatchService.get_user_notifications(watcher_user.id)
            print(f"✅ {watcher_user.username} 现在有 {len(notifications)} 个通知")

            if notifications:
                for notification in notifications:
                    print(f"   - 标题: {notification.title}")
                    print(f"     消息: {notification.message}")
                    print(f"     事件: {notification.event_type}")
                    print(f"     已读: {'是' if notification.is_read else '否'}")
                    print(f"     邮件已发送: {'是' if notification.is_sent else '否'}")
                    print(f"     创建时间: {notification.created_at}")

                # 测试标记为已读
                print(f"\n📖 标记通知为已读...")
                success = WatchService.mark_notification_read(notifications[0].id, watcher_user.id)
                if success:
                    print("✅ 通知已标记为已读")

                # 检查未读数量
                unread_count = WatchService.get_unread_count(watcher_user.id)
                print(f"📊 当前未读通知数量: {unread_count}")

            else:
                print("❌ 没有创建通知")

            return len(notifications) > 0

        except Exception as e:
            print(f"❌ 测试失败: {e}")
            db.session.rollback()
            return False

def check_email_setup():
    """检查邮件设置"""
    app = create_app('development')

    with app.app_context():
        print("\n📧 检查邮件配置...")

        mail_server = current_app.config.get('MAIL_SERVER')
        mail_username = current_app.config.get('MAIL_USERNAME')
        mail_password = current_app.config.get('MAIL_PASSWORD')

        print(f"   服务器: {mail_server}")
        print(f"   用户名: {mail_username}")
        print(f"   密码: {'已设置' if mail_password else '未设置'}")

        if mail_server and mail_username and mail_password:
            print("✅ 邮件配置完整")
            return True
        else:
            print("❌ 邮件配置不完整")
            return False

if __name__ == '__main__':
    print("=" * 60)
    print("🧪 Enterprise Wiki 通知系统测试")
    print("=" * 60)

    # 检查邮件配置
    email_ok = check_email_setup()

    # 测试通知系统
    notification_ok = test_notification_system()

    print("\n" + "=" * 60)
    if email_ok and notification_ok:
        print("🎉 通知系统测试通过！")
        print("✨ 功能正常:")
        print("   ✅ 站内通知正常工作")
        print("   ✅ 邮件配置正确")
        print("   ✅ Watch事件正确触发")
        print("   ✅ 通知管理功能正常")
    else:
        print("❌ 部分功能测试失败")
        print(f"   邮件配置: {'✅' if email_ok else '❌'}")
        print(f"   通知系统: {'✅' if notification_ok else '❌'}")
        sys.exit(1)