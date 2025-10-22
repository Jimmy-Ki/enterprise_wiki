from flask_login import current_user
from app import db
from app.models import Watch, WatchNotification, WatchTargetType, WatchEventType
from app.models.user import User
from app.models.wiki import Page, Category, Attachment
from datetime import datetime, timedelta
import json

class WatchService:
    """Watch功能服务类"""

    @staticmethod
    def create_watch(user_id, target_type, target_id, events=None):
        """
        创建watch记录
        :param user_id: 用户ID
        :param target_type: 目标类型 (WatchTargetType)
        :param target_id: 目标ID
        :param events: 监听的事件列表
        :return: Watch对象或None
        """
        try:
            # 检查是否已经存在
            existing_watch = Watch.query.filter_by(
                user_id=user_id,
                target_type=target_type,
                target_id=target_id
            ).first()

            if existing_watch:
                # 如果已存在，更新监听事件
                if events:
                    existing_watch.set_watched_events(events)
                    existing_watch.is_active = True
                    existing_watch.updated_at = datetime.utcnow()
                    db.session.add(existing_watch)
                return existing_watch

            # 创建新的watch记录
            watch = Watch(
                user_id=user_id,
                target_type=target_type,
                target_id=target_id
            )

            if events:
                watch.set_watched_events(events)

            db.session.add(watch)
            db.session.commit()
            return watch

        except Exception as e:
            db.session.rollback()
            print(f"Error creating watch: {e}")
            return None

    @staticmethod
    def remove_watch(user_id, target_type, target_id):
        """
        移除watch记录
        :param user_id: 用户ID
        :param target_type: 目标类型
        :param target_id: 目标ID
        :return: bool
        """
        try:
            watch = Watch.query.filter_by(
                user_id=user_id,
                target_type=target_type,
                target_id=target_id
            ).first()

            if watch:
                db.session.delete(watch)
                db.session.commit()
                return True
            return False

        except Exception as e:
            db.session.rollback()
            print(f"Error removing watch: {e}")
            return False

    @staticmethod
    def toggle_watch(user_id, target_type, target_id, events=None):
        """
        切换watch状态
        :param user_id: 用户ID
        :param target_type: 目标类型
        :param target_id: 目标ID
        :param events: 监听的事件列表
        :return: (Watch对象, 是否新创建)
        """
        watch = Watch.query.filter_by(
            user_id=user_id,
            target_type=target_type,
            target_id=target_id
        ).first()

        if watch:
            if watch.is_active:
                # 停用watch
                watch.is_active = False
                is_new = False
            else:
                # 重新激活watch
                watch.is_active = True
                if events:
                    watch.set_watched_events(events)
                watch.updated_at = datetime.utcnow()
                is_new = False

            db.session.add(watch)
            db.session.commit()
        else:
            # 创建新watch
            watch = WatchService.create_watch(user_id, target_type, target_id, events)
            is_new = True

        return watch, is_new

    @staticmethod
    def get_user_watches(user_id, target_type=None):
        """
        获取用户的所有watch记录
        :param user_id: 用户ID
        :param target_type: 目标类型过滤
        :return: Watch列表
        """
        query = Watch.query.filter_by(user_id=user_id, is_active=True)

        if target_type:
            query = query.filter_by(target_type=target_type)

        return query.all()

    @staticmethod
    def get_user_notifications(user_id, unread_only=False, limit=50):
        """
        获取用户的通知
        :param user_id: 用户ID
        :param unread_only: 是否只获取未读通知
        :param limit: 限制数量
        :return: WatchNotification列表
        """
        query = WatchNotification.query.filter_by(user_id=user_id)

        if unread_only:
            query = query.filter_by(is_read=False)

        return query.order_by(WatchNotification.created_at.desc()).limit(limit).all()

    @staticmethod
    def mark_notification_read(notification_id, user_id):
        """
        标记通知为已读
        :param notification_id: 通知ID
        :param user_id: 用户ID
        :return: bool
        """
        try:
            notification = WatchNotification.query.filter_by(
                id=notification_id,
                user_id=user_id
            ).first()

            if notification:
                notification.mark_as_read()
                db.session.commit()
                return True
            return False

        except Exception as e:
            db.session.rollback()
            print(f"Error marking notification as read: {e}")
            return False

    @staticmethod
    def mark_all_notifications_read(user_id):
        """
        标记用户所有通知为已读
        :param user_id: 用户ID
        :return: int - 标记为已读的通知数量
        """
        try:
            unread_notifications = WatchNotification.query.filter_by(
                user_id=user_id,
                is_read=False
            ).all()

            count = 0
            for notification in unread_notifications:
                notification.mark_as_read()
                count += 1

            db.session.commit()
            return count

        except Exception as e:
            db.session.rollback()
            print(f"Error marking all notifications as read: {e}")
            return 0

    @staticmethod
    def create_notification(watch, event_type, target_type, target_id, actor_id=None, extra_data=None):
        """
        创建通知
        :param watch: Watch对象
        :param event_type: 事件类型
        :param target_type: 目标类型
        :param target_id: 目标ID
        :param actor_id: 触发事件的用户ID
        :param extra_data: 额外数据
        :return: WatchNotification对象或None
        """
        try:
            notification = WatchNotification(
                user_id=watch.user_id,
                watch_id=watch.id,
                event_type=event_type,
                target_type=target_type,
                target_id=target_id,
                actor_id=actor_id
            )

            # 生成标题和消息
            notification.generate_title_and_message()

            db.session.add(notification)
            db.session.commit()

            # 获取用户信息并异步发送邮件通知
            try:
                from threading import Thread
                user = notification.user
                if user and user.email:
                    # 启动后台线程发送邮件，避免阻塞
                    Thread(target=WatchService._send_watch_notification_email,
                          args=(notification.id, user.id)).start()
            except Exception as e:
                print(f"Error starting watch notification email: {e}")
                # 不影响通知创建，只记录错误

            return notification

        except Exception as e:
            db.session.rollback()
            print(f"Error creating notification: {e}")
            return None

    @staticmethod
    def _send_watch_notification_email(notification_id, user_id):
        """
        异步发送watch通知邮件的内部方法
        :param notification_id: 通知ID
        :param user_id: 用户ID
        """
        try:
            from app import mail, create_app
            from flask_mail import Message
            from app.models import WatchNotification, User

            # 创建新的应用上下文（因为这是在后台线程中运行）
            app = create_app()
            with app.app_context():
                # 重新获取通知和用户信息
                notification = WatchNotification.query.get(notification_id)
                user = User.query.get(user_id)

                if not notification or not user or not user.email:
                    return

                # 检查邮件是否已发送
                if notification.is_sent:
                    return

                # 创建邮件内容
                site_url = app.config.get('SITE_URL', 'http://localhost:5001')

                # URL部分（如果存在）
                url_section = ''
                if notification.url:
                    url_section = f'''
                    <p style="margin-top: 15px;">
                        <a href="{site_url}{notification.url}"
                           style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block;">
                            查看详情
                        </a>
                    </p>
                    '''

                url_section_text = ''
                if notification.url:
                    url_section_text = f'查看详情: {site_url}{notification.url}'

                email_html = f'''
                <h2>Enterprise Wiki 通知</h2>
                <p>你好 {user.name or user.username},</p>

                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #495057; margin-top: 0;">{notification.title}</h3>
                    <p style="color: #6c757d; line-height: 1.5;">{notification.message}</p>
                    {url_section}
                </div>

                <p style="color: #6c757d; font-size: 14px;">
                    此邮件由 Enterprise Wiki 系统自动发送。<br>
                    如不想接收此类通知，请访问<a href="{site_url}/profile">个人设置</a>管理通知偏好。
                </p>
                '''

                email_text = f'''
                Enterprise Wiki 通知

                你好 {user.name or user.username},

                {notification.title}
                {notification.message}

                {url_section_text}

                此邮件由 Enterprise Wiki 系统自动发送。
                如不想接收此类通知，请访问 {site_url}/profile 管理通知偏好。
                '''

                msg = Message(
                    subject=f'Enterprise Wiki: {notification.title}',
                    sender=app.config.get('MAIL_SENDER', 'noreply@enterprise-wiki.com'),
                    recipients=[user.email],
                    html=email_html,
                    body=email_text
                )

                mail.send(msg)

                # 标记邮件已发送
                notification.is_sent = True
                db.session.commit()

        except Exception as e:
            print(f"Error sending watch notification email (notification_id={notification_id}): {e}")
            # 不影响主流程，只记录错误

    @staticmethod
    def trigger_event(event_type, target_type, target_id, actor_id=None):
        """
        触发事件，创建相关通知
        :param event_type: 事件类型
        :param target_type: 目标类型
        :param target_id: 目标ID
        :param actor_id: 触发事件的用户ID
        :return: 创建的通知数量
        """
        try:
            notifications_created = 0
            watches = []  # 初始化watches列表

            if target_type == WatchTargetType.PAGE:
                # 页面相关事件
                watches = Watch.find_watches_for_event(target_type, target_id, event_type)

                # 如果是页面创建事件，还要检查页面所在分类的watch
                if event_type == WatchEventType.PAGE_CREATED:
                    page = Page.query.get(target_id)
                    if page and page.category_id:
                        category_watches = Watch.find_watches_for_category_event(
                            page.category_id, event_type
                        )
                        watches.extend(category_watches)

            elif target_type == WatchTargetType.CATEGORY:
                # 分类相关事件
                watches = Watch.find_watches_for_category_event(target_id, event_type)

            # 为每个watch创建通知
            for watch in watches:
                # 不给触发事件的人自己发通知
                if watch.user_id != actor_id:
                    notification = WatchService.create_notification(
                        watch, event_type, target_type, target_id, actor_id
                    )
                    if notification:
                        notifications_created += 1

            return notifications_created

        except Exception as e:
            print(f"Error triggering event: {e}")
            return 0

    @staticmethod
    def get_unread_count(user_id):
        """
        获取用户未读通知数量
        :param user_id: 用户ID
        :return: 未读通知数量
        """
        return WatchNotification.query.filter_by(
            user_id=user_id,
            is_read=False
        ).count()

    @staticmethod
    def cleanup_old_notifications(days_old=30):
        """
        清理旧通知
        :param days_old: 保留天数
        :return: 清理的通知数量
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            old_notifications = WatchNotification.query.filter(
                WatchNotification.created_at < cutoff_date
            ).all()

            count = len(old_notifications)
            for notification in old_notifications:
                db.session.delete(notification)

            db.session.commit()
            return count

        except Exception as e:
            db.session.rollback()
            print(f"Error cleaning up old notifications: {e}")
            return 0

# 便捷函数
def watch_page(user_id, page_id, events=None):
    """关注页面"""
    if events is None:
        events = ['page_updated', 'page_deleted', 'attachment_added', 'attachment_removed']
    return WatchService.create_watch(user_id, WatchTargetType.PAGE, page_id, events)

def watch_category(user_id, category_id, events=None):
    """关注分类"""
    if events is None:
        events = ['page_created', 'page_updated', 'page_deleted', 'category_updated']
    return WatchService.create_watch(user_id, WatchTargetType.CATEGORY, category_id, events)

def unwatch_page(user_id, page_id):
    """取消关注页面"""
    return WatchService.remove_watch(user_id, WatchTargetType.PAGE, page_id)

def unwatch_category(user_id, category_id):
    """取消关注分类"""
    return WatchService.remove_watch(user_id, WatchTargetType.CATEGORY, category_id)

def process_pending_watch_events():
    """
    处理待处理的watch事件
    这个函数应该在请求处理完成后调用，避免数据库会话冲突
    """
    try:
        from flask import current_app
        if not hasattr(current_app, '_pending_watch_events'):
            return 0

        pending_events = current_app._pending_watch_events.copy()
        current_app._pending_watch_events = []

        total_notifications = 0
        for event in pending_events:
            notifications_created = WatchService.trigger_event(
                event_type=event['event_type'],
                target_type=event['target_type'],
                target_id=event['target_id'],
                actor_id=event.get('actor_id')
            )
            total_notifications += notifications_created

        return total_notifications

    except Exception as e:
        print(f"Error processing pending watch events: {e}")
        return 0