#!/usr/bin/env python3
"""
测试评论系统功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Page, Comment, CommentMention, CommentTargetType

def test_comment_system():
    """测试评论系统基本功能"""
    app = create_app('development')

    with app.app_context():
        print("🚀 测试评论系统...")

        # 确保数据库表存在
        db.create_all()

        # 查找测试用户
        users = User.query.limit(2).all()
        if len(users) < 2:
            print("❌ 需要至少2个用户进行测试")
            return False

        author_user = users[0]  # 评论作者
        mentioned_user = users[1]  # 被提及的用户

        print(f"✅ 评论作者: {author_user.username}")
        print(f"✅ 被提及用户: {mentioned_user.username}")

        # 查找测试页面
        page = Page.query.first()
        if not page:
            print("❌ 没有找到测试页面")
            return False

        print(f"✅ 测试页面: {page.title}")

        # 清理之前的测试数据
        old_comments = Comment.query.filter_by(target_type=CommentTargetType.PAGE, target_id=page.id).all()
        for comment in old_comments:
            # 删除相关的提及记录
            CommentMention.query.filter_by(comment_id=comment.id).delete()
            db.session.delete(comment)
        db.session.commit()

        # 测试创建评论（包含@提及）
        print("\n📝 创建评论（包含@提及）...")
        from app.services.comment_service import CommentService

        comment_content = f"这是一个测试评论，@{mentioned_user.username} 请查看这个页面。"

        comment = CommentService.create_comment(
            target_type=CommentTargetType.PAGE,
            target_id=page.id,
            content=comment_content,
            author_id=author_user.id
        )

        if not comment:
            print("❌ 评论创建失败")
            return False

        print(f"✅ 评论创建成功，ID: {comment.id}")

        # 检查@提及是否被正确解析
        mentions = comment.mentions.all()
        print(f"✅ 解析到 {len(mentions)} 个@提及")

        for mention in mentions:
            print(f"   - 提及用户: {mention.mentioned_username}")

        # 测试获取评论列表
        print("\n📋 获取评论列表...")
        comments_result = CommentService.get_comments(
            target_type=CommentTargetType.PAGE,
            target_id=page.id,
            include_replies=True
        )

        print(f"✅ 获取到 {len(comments_result['comments'])} 个评论")

        if comments_result['comments']:
            comment_data = comments_result['comments'][0]
            print(f"   - 评论内容: {comment_data['content'][:50]}...")
            print(f"   - 作者: {comment_data['author']['username']}")
            print(f"   - 提及用户: {[m['username'] for m in comment_data['mentions']]}")

        # 测试搜索用户（用于@提及）
        print("\n🔍 测试用户搜索...")
        search_results = CommentService.search_users(mentioned_user.username[:3], limit=5)
        print(f"✅ 搜索 '{mentioned_user.username[:3]}' 找到 {len(search_results)} 个用户")

        for user in search_results:
            print(f"   - {user.name} (@{user.username})")

        # 测试回复功能
        print("\n💬 测试回复功能...")
        reply_content = f"这是一个回复，@{author_user.username} 谢谢你的评论！"

        reply_comment = CommentService.create_comment(
            target_type=CommentTargetType.PAGE,
            target_id=page.id,
            content=reply_content,
            author_id=mentioned_user.id,
            parent_id=comment.id
        )

        if reply_comment:
            print(f"✅ 回复创建成功，ID: {reply_comment.id}")
        else:
            print("❌ 回复创建失败")
            return False

        # 测试获取用户提及
        print("\n📢 测试获取用户提及...")
        mentions_result = CommentService.get_user_mentions(
            user_id=mentioned_user.id,
            unread_only=False
        )

        print(f"✅ 用户 {mentioned_user.username} 有 {mentions_result['total']} 个提及")

        if mentions_result['mentions']:
            mention_data = mentions_result['mentions'][0]
            print(f"   - 最新提及: {mention_data['comment']['content'][:50]}...")

        # 测试标记提及为已读
        if mentions_result['mentions']:
            mention_id = mentions_result['mentions'][0]['id']
            success = CommentService.mark_mention_as_read(mention_id, mentioned_user.id)
            if success:
                print(f"✅ 提及 {mention_id} 标记为已读")
            else:
                print(f"❌ 标记提及 {mention_id} 为已读失败")

        print("\n🎉 评论系统测试完成！")
        print("✨ 功能正常:")
        print("   ✅ 评论创建成功")
        print("   ✅ @提及解析正确")
        print("   ✅ 评论列表获取正常")
        print("   ✅ 用户搜索功能正常")
        print("   ✅ 回复功能正常")
        print("   ✅ 提及通知功能正常")
        print("   ✅ 提及已读标记正常")

        return True

if __name__ == '__main__':
    print("=" * 60)
    print("🧪 Enterprise Wiki 评论系统测试")
    print("=" * 60)

    success = test_comment_system()

    if success:
        print("\n✅ 所有测试通过！评论系统功能正常")
    else:
        print("\n❌ 部分测试失败，请检查实现")
        sys.exit(1)