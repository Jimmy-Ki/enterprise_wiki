#!/usr/bin/env python3
"""
测试单次通知触发，避免重复
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Page, Watch, WatchTargetType, WatchEventType
from app.services.watch_service import WatchService, process_pending_watch_events
from flask import current_app

def test_single_notification():
    """测试单次通知触发"""
    app = create_app('development')

    with app.app_context():
        print("🚀 测试单次通知触发...")

        # 清理之前的通知和事件
        if hasattr(current_app, '_pending_watch_events'):
            current_app._pending_watch_events.clear()

        # 确保数据库表存在
        db.create_all()

        # 查找用户
        watcher_user = User.query.filter_by(username='admin').first()
        if not watcher_user:
            print("❌ 没有找到admin用户")
            return False

        # 查找测试页面
        page = Page.query.filter_by(slug='jiang-meng-qi').first()
        if not page:
            print("❌ 没有找到测试页面")
            return False

        print(f"✅ 关注者: {watcher_user.username}")
        print(f"✅ 测试页面: {page.title}")

        # 清理之前的通知
        from app.models.watch import WatchNotification
        old_notifications = WatchNotification.query.filter_by(user_id=watcher_user.id).all()
        for notification in old_notifications:
            db.session.delete(notification)
        db.session.commit()

        # 创建关注
        watch = WatchService.create_watch(
            user_id=watcher_user.id,
            target_type=WatchTargetType.PAGE,
            target_id=page.id,
            events=['page_updated', 'page_deleted', 'attachment_added']
        )

        if not watch:
            print("❌ 关注创建失败")
            return False

        print(f"✅ 创建关注成功")

        # 清理待处理事件
        current_app._pending_watch_events = []

        # 手动添加一个测试事件
        current_app._pending_watch_events.append({
            'event_type': WatchEventType.PAGE_UPDATED,
            'target_type': WatchTargetType.PAGE,
            'target_id': page.id,
            'actor_id': 2  # 假设是另一个用户
        })

        print(f"✅ 添加了1个测试事件")

        # 检查初始通知数量
        initial_count = WatchService.get_unread_count(watcher_user.id)
        print(f"📊 初始未读通知数量: {initial_count}")

        # 处理事件
        print("\n🔄 处理事件...")
        notifications_count = process_pending_watch_events()
        print(f"✅ 处理了 {notifications_count} 个事件")

        # 检查最终通知
        final_notifications = WatchService.get_user_notifications(watcher_user.id)
        print(f"✅ 最终有 {len(final_notifications)} 个通知")

        # 验证没有重复
        if len(final_notifications) == 1:
            notification = final_notifications[0]
            print(f"   - 标题: {notification.title}")
            print(f"   - 消息: {notification.message}")
            print(f"   - 邮件已发送: {'是' if notification.is_sent else '否'}")
            print("\n🎉 单次通知触发测试成功！")
            return True
        else:
            print(f"❌ 通知数量异常: {len(final_notifications)} (期望: 1)")
            for i, notification in enumerate(final_notifications):
                print(f"   通知 {i+1}: {notification.title}")
            return False

if __name__ == '__main__':
    print("=" * 50)
    print("🧪 单次通知触发测试")
    print("=" * 50)

    success = test_single_notification()

    if success:
        print("\n✅ 测试通过！通知不再重复触发")
    else:
        print("\n❌ 测试失败，通知仍有重复")
        sys.exit(1)