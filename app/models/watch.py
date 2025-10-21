from datetime import datetime
from app import db
from sqlalchemy import Enum
import enum

class WatchTargetType(enum.Enum):
    PAGE = 'page'
    CATEGORY = 'category'

class WatchEventType(enum.Enum):
    PAGE_CREATED = 'page_created'
    PAGE_UPDATED = 'page_updated'
    PAGE_DELETED = 'page_deleted'
    CATEGORY_CREATED = 'category_created'
    CATEGORY_UPDATED = 'category_updated'
    CATEGORY_DELETED = 'category_deleted'
    ATTACHMENT_ADDED = 'attachment_added'
    ATTACHMENT_REMOVED = 'attachment_removed'
    COMMENT_ADDED = 'comment_added'
    COMMENT_MENTION = 'comment_mention'

class Watch(db.Model):
    """用户关注某个页面或分类"""
    __tablename__ = 'watches'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    target_type = db.Column(Enum(WatchTargetType), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)  # 页面ID或分类ID

    # 监听的事件类型（JSON数组存储）
    watched_events = db.Column(db.Text, default='[]')  # JSON array of WatchEventType strings

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='watches')

    # 复合索引，确保用户不会重复关注同一个目标
    __table_args__ = (
        db.Index('ix_watches_user_target', 'user_id', 'target_type', 'target_id', unique=True),
        db.Index('ix_watches_target', 'target_type', 'target_id'),
    )

    def __init__(self, **kwargs):
        super(Watch, self).__init__(**kwargs)
        if not self.watched_events:
            # 默认监听所有相关事件
            if self.target_type == WatchTargetType.PAGE:
                self.watched_events = '["page_updated", "page_deleted", "attachment_added", "attachment_removed"]'
            elif self.target_type == WatchTargetType.CATEGORY:
                self.watched_events = '["page_created", "page_updated", "page_deleted", "category_updated"]'

    def __repr__(self):
        return f'<Watch {self.user.username} -> {self.target_type.value}:{self.target_id}>'

    def get_watched_events(self):
        """获取监听的事件类型列表"""
        import json
        return json.loads(self.watched_events) if self.watched_events else []

    def set_watched_events(self, events):
        """设置监听的事件类型"""
        import json
        if isinstance(events, list):
            self.watched_events = json.dumps([e.value if hasattr(e, 'value') else e for e in events])
        else:
            self.watched_events = json.dumps([])

    def is_watching_event(self, event_type):
        """检查是否在监听特定事件"""
        watched_events = self.get_watched_events()
        event_value = event_type.value if hasattr(event_type, 'value') else event_type
        return event_value in watched_events

    @staticmethod
    def find_watches_for_event(target_type, target_id, event_type):
        """查找监听特定事件的所有watch记录"""
        event_value = event_type.value if hasattr(event_type, 'value') else event_type
        watches = Watch.query.filter_by(
            target_type=target_type,
            target_id=target_id,
            is_active=True
        ).all()

        # 过滤出监听了此事件的watch
        result = []
        for watch in watches:
            watched_events = watch.get_watched_events()
            if event_value in watched_events:
                result.append(watch)

        return result

    @staticmethod
    def find_watches_for_category_event(category_id, event_type):
        """查找监听分类事件的所有watch记录（包括父分类的watch）"""
        from app.models.wiki import Category

        # 获取分类及其所有父分类
        category = Category.query.get(category_id)
        if not category:
            return []

        target_ids = [category_id]
        current = category
        while current.parent:
            target_ids.append(current.parent.id)
            current = current.parent

        # 查找这些分类的watch记录
        watches = []
        for target_id in target_ids:
            category_watches = Watch.query.filter_by(
                target_type=WatchTargetType.CATEGORY,
                target_id=target_id,
                is_active=True
            ).all()
            watches.extend([w for w in category_watches if w.is_watching_event(event_type)])

        return watches

class WatchNotification(db.Model):
    """Watch通知记录"""
    __tablename__ = 'watch_notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    watch_id = db.Column(db.Integer, db.ForeignKey('watches.id'), nullable=False)

    # 事件信息
    event_type = db.Column(db.Enum(WatchEventType), nullable=False)
    target_type = db.Column(db.Enum(WatchTargetType), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)

    # 触发事件的信息
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # 触发事件的用户
    title = db.Column(db.String(255))  # 通知标题
    message = db.Column(db.Text)  # 通知消息
    url = db.Column(db.String(500))  # 相关链接

    # 状态和时间
    is_read = db.Column(db.Boolean, default=False)
    is_sent = db.Column(db.Boolean, default=False)  # 是否已发送邮件通知
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='watch_notifications')
    watch = db.relationship('Watch', backref='notifications')
    actor = db.relationship('User', foreign_keys=[actor_id])

    __table_args__ = (
        db.Index('ix_watch_notifications_user_unread', 'user_id', 'is_read'),
        db.Index('ix_watch_notifications_created', 'created_at'),
    )

    def __repr__(self):
        return f'<WatchNotification {self.user.username} - {self.event_type.value}>'

    def mark_as_read(self):
        """标记为已读"""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()
            db.session.add(self)

    def generate_title_and_message(self):
        """生成通知标题和消息"""
        from app.models.wiki import Page, Category

        # 获取目标对象
        target = None
        if self.target_type == WatchTargetType.PAGE:
            target = Page.query.get(self.target_id)
        elif self.target_type == WatchTargetType.CATEGORY:
            target = Category.query.get(self.target_id)

        actor_name = self.actor.username if self.actor else 'Unknown'

        # 根据事件类型生成标题和消息
        if self.event_type == WatchEventType.PAGE_CREATED:
            self.title = f'New page created: {target.title if target else "Unknown"}'
            self.message = f'{actor_name} created a new page "{target.title if target else "Unknown"}"'
            self.url = f'/page/{target.slug}' if target else None

        elif self.event_type == WatchEventType.PAGE_UPDATED:
            self.title = f'Page updated: {target.title if target else "Unknown"}'
            self.message = f'{actor_name} updated the page "{target.title if target else "Unknown"}"'
            self.url = f'/page/{target.slug}' if target else None

        elif self.event_type == WatchEventType.PAGE_DELETED:
            self.title = f'Page deleted'
            self.message = f'{actor_name} deleted a page'
            self.url = None

        elif self.event_type == WatchEventType.CATEGORY_CREATED:
            self.title = f'New category created: {target.name if target else "Unknown"}'
            self.message = f'{actor_name} created a new category "{target.name if target else "Unknown"}"'
            self.url = f'/category/{target.id}' if target else None

        elif self.event_type == WatchEventType.CATEGORY_UPDATED:
            self.title = f'Category updated: {target.name if target else "Unknown"}'
            self.message = f'{actor_name} updated the category "{target.name if target else "Unknown"}"'
            self.url = f'/category/{target.id}' if target else None

        elif self.event_type == WatchEventType.CATEGORY_DELETED:
            self.title = f'Category deleted'
            self.message = f'{actor_name} deleted a category'
            self.url = None

        elif self.event_type == WatchEventType.ATTACHMENT_ADDED:
            self.title = f'Attachment added to: {target.title if target else "Unknown"}'
            self.message = f'{actor_name} added an attachment to "{target.title if target else "Unknown"}"'
            self.url = f'/page/{target.slug}' if target else None

        elif self.event_type == WatchEventType.ATTACHMENT_REMOVED:
            self.title = f'Attachment removed from: {target.title if target else "Unknown"}'
            self.message = f'{actor_name} removed an attachment from "{target.title if target else "Unknown"}"'
            self.url = f'/page/{target.slug}' if target else None

        elif self.event_type == WatchEventType.COMMENT_ADDED:
            # 获取评论内容
            from app.models.comment import Comment
            comment = Comment.query.get(self.target_id) if hasattr(self, 'comment_id') else None

            if comment:
                if comment.target_type.value == 'page':
                    page_target = Page.query.get(comment.target_id)
                    if page_target:
                        self.title = f'New comment on: {page_target.title}'
                        self.message = f'{actor_name} commented on "{page_target.title}": "{comment.content[:100]}{"..." if len(comment.content) > 100 else ""}"'
                        self.url = f'/page/{page_target.slug}#comment-{comment.id}'
                elif comment.target_type.value == 'attachment':
                    attachment = Attachment.query.get(comment.target_id)
                    if attachment and attachment.page:
                        self.title = f'New comment on attachment in: {attachment.page.title}'
                        self.message = f'{actor_name} commented on an attachment in "{attachment.page.title}": "{comment.content[:100]}{"..." if len(comment.content) > 100 else ""}"'
                        self.url = f'/page/{attachment.page.slug}#comment-{comment.id}'
            else:
                self.title = 'New comment'
                self.message = f'{actor_name} added a new comment'
                self.url = None

        elif self.event_type == WatchEventType.COMMENT_MENTION:
            # 获取提及的评论内容
            from app.models.comment import Comment
            comment = Comment.query.get(self.target_id) if hasattr(self, 'comment_id') else None

            if comment:
                if comment.target_type.value == 'page':
                    page_target = Page.query.get(comment.target_id)
                    if page_target:
                        self.title = f'You were mentioned in a comment on: {page_target.title}'
                        self.message = f'{actor_name} mentioned you in a comment on "{page_target.title}": "{comment.content[:100]}{"..." if len(comment.content) > 100 else ""}"'
                        self.url = f'/page/{page_target.slug}#comment-{comment.id}'
                elif comment.target_type.value == 'attachment':
                    attachment = Attachment.query.get(comment.target_id)
                    if attachment and attachment.page:
                        self.title = f'You were mentioned in a comment on: {attachment.page.title}'
                        self.message = f'{actor_name} mentioned you in a comment on "{attachment.page.title}": "{comment.content[:100]}{"..." if len(comment.content) > 100 else ""}"'
                        self.url = f'/page/{attachment.page.slug}#comment-{comment.id}'
            else:
                self.title = 'You were mentioned in a comment'
                self.message = f'{actor_name} mentioned you in a comment'
                self.url = None

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'event_type': self.event_type.value,
            'target_type': self.target_type.value,
            'target_id': self.target_id,
            'title': self.title,
            'message': self.message,
            'url': self.url,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat(),
            'actor': self.actor.username if self.actor else None,
        }