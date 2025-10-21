from flask_login import current_user
from app import db
from app.models import Comment, CommentMention, CommentTargetType, User
from app.models.user import User
from app.models.wiki import Page, Attachment
from datetime import datetime
import re

class CommentService:
    """评论功能服务类"""

    @staticmethod
    def create_comment(target_type, target_id, content, author_id=None, parent_id=None):
        """
        创建评论
        :param target_type: 目标类型 (CommentTargetType)
        :param target_id: 目标ID
        :param content: 评论内容
        :param author_id: 作者ID，默认为当前用户
        :param parent_id: 父评论ID（用于回复）
        :return: Comment对象或None
        """
        try:
            if author_id is None:
                if current_user.is_authenticated:
                    author_id = current_user.id
                else:
                    return None

            # 验证目标是否存在
            target = CommentService.get_target(target_type, target_id)
            if not target:
                return None

            # 验证父评论
            parent = None
            if parent_id:
                parent = Comment.query.get(parent_id)
                if not parent or parent.is_deleted:
                    return None

            # 创建评论
            comment = Comment(
                content=content,
                target_type=target_type,
                target_id=target_id,
                author_id=author_id,
                parent_id=parent_id
            )

            db.session.add(comment)
            db.session.commit()

            # 处理@提及通知
            CommentService.process_mention_notifications(comment)

            # 触发评论事件
            CommentService.trigger_comment_event(comment, 'created')

            return comment

        except Exception as e:
            db.session.rollback()
            print(f"Error creating comment: {e}")
            return None

    @staticmethod
    def update_comment(comment_id, content, author_id=None):
        """
        更新评论
        :param comment_id: 评论ID
        :param content: 新内容
        :param author_id: 编辑者ID，默认为当前用户
        :return: Comment对象或None
        """
        try:
            if author_id is None:
                if current_user.is_authenticated:
                    author_id = current_user.id
                else:
                    return None

            comment = Comment.query.get(comment_id)
            if not comment or comment.is_deleted:
                return None

            # 检查权限
            if comment.author_id != author_id:
                return None

            # 更新内容
            comment.content = content
            comment.is_edited = True
            comment.updated_at = datetime.utcnow()

            db.session.commit()

            # 重新处理@提及通知
            # 删除旧的提及记录
            CommentMention.query.filter_by(comment_id=comment_id).delete()

            # 处理新的提及通知
            CommentService.process_mention_notifications(comment)

            # 触发评论事件
            CommentService.trigger_comment_event(comment, 'updated')

            return comment

        except Exception as e:
            db.session.rollback()
            print(f"Error updating comment: {e}")
            return None

    @staticmethod
    def delete_comment(comment_id, author_id=None):
        """
        删除评论
        :param comment_id: 评论ID
        :param author_id: 删除者ID，默认为当前用户
        :return: bool
        """
        try:
            if author_id is None:
                if current_user.is_authenticated:
                    author_id = current_user.id
                else:
                    return False

            comment = Comment.query.get(comment_id)
            if not comment or comment.is_deleted:
                return False

            # 检查权限
            if comment.author_id != author_id:
                return False

            # 软删除
            comment.is_deleted = True
            comment.updated_at = datetime.utcnow()

            db.session.commit()

            # 触发评论事件
            CommentService.trigger_comment_event(comment, 'deleted')

            return True

        except Exception as e:
            db.session.rollback()
            print(f"Error deleting comment: {e}")
            return False

    @staticmethod
    def get_comments(target_type, target_id, include_replies=True, page=1, per_page=20):
        """
        获取目标的所有评论
        :param target_type: 目标类型
        :param target_id: 目标ID
        :param include_replies: 是否包含回复
        :param page: 页码
        :param per_page: 每页数量
        :return: 分页评论列表
        """
        query = Comment.query.filter_by(
            target_type=target_type,
            target_id=target_id,
            parent_id=None,  # 只获取顶级评论
            is_deleted=False
        ).order_by(Comment.created_at.desc())

        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        comments = []
        for comment in pagination.items:
            comment_dict = comment.to_dict()
            if include_replies:
                # 获取回复
                replies = Comment.query.filter_by(
                    parent_id=comment.id,
                    is_deleted=False
                ).order_by(Comment.created_at.asc()).all()
                comment_dict['replies'] = [reply.to_dict() for reply in replies]
            comments.append(comment_dict)

        return {
            'comments': comments,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }

    @staticmethod
    def get_user_comments(user_id, page=1, per_page=20):
        """
        获取用户的所有评论
        :param user_id: 用户ID
        :param page: 页码
        :param per_page: 每页数量
        :return: 分页评论列表
        """
        query = Comment.query.filter_by(
            author_id=user_id,
            is_deleted=False
        ).order_by(Comment.created_at.desc())

        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        return {
            'comments': [comment.to_dict() for comment in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }

    @staticmethod
    def get_target(target_type, target_id):
        """获取目标对象"""
        if target_type == CommentTargetType.PAGE:
            return Page.query.get(target_id)
        elif target_type == CommentTargetType.ATTACHMENT:
            return Attachment.query.get(target_id)
        return None

    @staticmethod
    def process_mention_notifications(comment):
        """处理@提及通知"""
        mentions = comment.mentions.all()
        for mention in mentions:
            # 创建watch通知
            CommentService.create_mention_notification(comment, mention)

            # 发送邮件通知
            CommentService.send_mention_email(comment, mention)

    @staticmethod
    def create_mention_notification(comment, mention):
        """创建@提及的站内通知"""
        try:
            from app.models import WatchNotification, WatchEventType
            from app.services.watch_service import WatchService

            # 创建watch通知
            notification = WatchNotification(
                user_id=mention.mentioned_user_id,
                event_type=WatchEventType.COMMENT_MENTION,
                target_type=comment.target_type,
                target_id=comment.id,
                actor_id=comment.author_id
            )

            # 生成标题和消息
            notification.generate_title_and_message()

            db.session.add(notification)
            db.session.commit()

            # 发送邮件通知
            WatchService.create_notification(
                watch=None,  # 没有关联的watch记录
                event_type=WatchEventType.COMMENT_MENTION,
                target_type=comment.target_type,
                target_id=comment.id,
                actor_id=comment.author_id
            )

        except Exception as e:
            print(f"Error creating mention notification: {e}")

    @staticmethod
    def send_mention_email(comment, mention):
        """发送@提及的邮件通知"""
        try:
            from flask import current_app
            from flask_mail import Message
            from app import mail

            user = mention.mentioned_user
            if not user or not user.email:
                return

            # 获取目标信息
            target = CommentService.get_target(comment.target_type, comment.target_id)
            target_name = target.title if hasattr(target, 'title') else f'{comment.target_type.value}:{comment.target_id}'

            # 构建URL
            site_url = current_app.config.get('SITE_URL', 'http://localhost:5001')
            if comment.target_type == CommentTargetType.PAGE:
                comment_url = f"{site_url}/page/{target.slug}"
            else:
                comment_url = f"{site_url}/"

            # 发送邮件
            email_html = f'''
            <h2>Enterprise Wiki - You were mentioned</h2>
            <p>Hi {user.name or user.username},</p>
            <p><strong>{comment.author.name or comment.author.username}</strong> mentioned you in a comment on <strong>{target_name}</strong>.</p>

            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0;"><em>{comment.content}</em></p>
                <small style="color: #6c757d;">Posted on {comment.created_at.strftime('%Y-%m-%d %H:%M')}</small>
            </div>

            <p style="margin-top: 20px;">
                <a href="{comment_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block;">
                    View Comment
                </a>
            </p>

            <p style="color: #6c757d; font-size: 14px;">
                This email was sent because you were mentioned in a comment on Enterprise Wiki.
            </p>
            '''

            email_text = f'''
            Enterprise Wiki - You were mentioned

            Hi {user.name or user.username},

            {comment.author.name or comment.author.username} mentioned you in a comment on {target_name}.

            "{comment.content}"

            View the comment here: {comment_url}

            This email was sent because you were mentioned in a comment on Enterprise Wiki.
            '''

            msg = Message(
                subject=f'Enterprise Wiki: You were mentioned by {comment.author.name or comment.author.username}',
                sender=current_app.config.get('MAIL_SENDER', 'noreply@enterprise-wiki.com'),
                recipients=[user.email],
                html=email_html,
                body=email_text
            )

            mail.send(msg)

            # 标记通知已发送
            mention.notification_sent = True
            db.session.commit()

        except Exception as e:
            print(f"Error sending mention email: {e}")

    @staticmethod
    def trigger_comment_event(comment, action):
        """触发评论事件"""
        try:
            from app.models import WatchEventType, WatchTargetType
            from app.services.watch_service import WatchService

            if action == 'created':
                # 触发新评论事件，通知关注目标页面的用户
                WatchService.trigger_event(
                    event_type=WatchEventType.COMMENT_ADDED,
                    target_type=comment.target_type,
                    target_id=comment.target_id,
                    actor_id=comment.author_id
                )

        except Exception as e:
            print(f"Error triggering comment event: {e}")

    @staticmethod
    def search_users(query, limit=10):
        """搜索用户（用于@提及功能）"""
        try:
            users = User.query.filter(
                User.is_active == True,
                db.or_(
                    User.username.ilike(f'%{query}%'),
                    User.name.ilike(f'%{query}%'),
                    User.email.ilike(f'%{query}%')
                )
            ).limit(limit).all()

            return [
                {
                    'id': user.id,
                    'username': user.username,
                    'name': user.name,
                    'email': user.email,
                    'avatar': user.avatar or '/static/img/default-avatar.png'
                }
                for user in users
            ]
        except Exception as e:
            print(f"Error searching users: {e}")
            return []

    @staticmethod
    def mark_mention_as_read(mention_id, user_id):
        """标记提及为已读"""
        try:
            mention = CommentMention.query.filter_by(
                id=mention_id,
                mentioned_user_id=user_id
            ).first()

            if mention and not mention.is_read:
                mention.mark_as_read()
                db.session.commit()
                return True

            return False
        except Exception as e:
            db.session.rollback()
            print(f"Error marking mention as read: {e}")
            return False

    @staticmethod
    def get_user_mentions(user_id, unread_only=False, page=1, per_page=20):
        """获取用户的@提及"""
        query = CommentMention.query.filter_by(mentioned_user_id=user_id)

        if unread_only:
            query = query.filter_by(is_read=False)

        query = query.order_by(CommentMention.created_at.desc())

        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        return {
            'mentions': [
                {
                    'id': mention.id,
                    'comment': mention.comment.to_dict(),
                    'is_read': mention.is_read,
                    'created_at': mention.created_at.isoformat()
                }
                for mention in pagination.items if not mention.comment.is_deleted
            ],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }

# 便捷函数
def add_page_comment(page_id, content, author_id=None, parent_id=None):
    """为页面添加评论"""
    return CommentService.create_comment(CommentTargetType.PAGE, page_id, content, author_id, parent_id)

def add_attachment_comment(attachment_id, content, author_id=None, parent_id=None):
    """为附件添加评论"""
    return CommentService.create_comment(CommentTargetType.ATTACHMENT, attachment_id, content, author_id, parent_id)