#!/usr/bin/env python3
"""
测试页面保存功能是否修复了watch相关错误
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Page, Watch, WatchTargetType, WatchEventType
from app.services.watch_service import WatchService, process_pending_watch_events
from datetime import datetime

def test_page_save_with_watch():
    """测试在有watch的情况下保存页面"""
    app = create_app('development')

    with app.app_context():
        print("🚀 测试页面保存功能...")

        # 确保数据库表存在
        db.create_all()

        # 查找或创建用户
        user = User.query.first()
        if not user:
            print("❌ 没有找到用户")
            return False

        print(f"✅ 找到用户: {user.username}")

        # 查找或创建测试页面
        page = Page.query.first()
        if not page:
            print("❌ 没有找到页面")
            return False

        print(f"✅ 找到页面: {page.title}")

        # 创建 watch
        print("\n📝 创建 Watch...")
        watch = WatchService.create_watch(
            user_id=user.id,
            target_type=WatchTargetType.PAGE,
            target_id=page.id,
            events=['page_updated', 'page_deleted']
        )

        if watch:
            print(f"✅ Watch 创建成功")
        else:
            print("❌ Watch 创建失败")
            return False

        # 模拟页面更新
        print("\n✏️ 模拟页面更新...")

        try:
            # 保存原始内容
            original_content = page.content
            original_updated = page.updated_at

            # 修改页面内容
            page.content = original_content + f"\n\n测试修改时间: {datetime.now()}"
            page.last_editor_id = user.id
            page.updated_at = datetime.utcnow()

            # 标记内容已更改
            page._watch_content_changed = True

            # 保存到数据库
            db.session.commit()

            print("✅ 页面保存成功")

            # 处理pending events
            print("\n🔄 处理待处理的watch事件...")
            notifications_count = process_pending_watch_events()
            print(f"✅ 处理了 {notifications_count} 个通知")

            # 检查通知
            notifications = WatchService.get_user_notifications(user.id)
            print(f"✅ 用户有 {len(notifications)} 个通知")

            return True

        except Exception as e:
            print(f"❌ 页面保存失败: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    print("=" * 50)
    print("🧪 测试页面保存 + Watch 功能")
    print("=" * 50)

    success = test_page_save_with_watch()

    print("\n" + "=" * 50)
    if success:
        print("🎉 页面保存功能测试通过！")
        print("✅ Watch 功能不再干扰页面保存")
    else:
        print("❌ 页面保存功能仍有问题")
        sys.exit(1)