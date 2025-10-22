from datetime import datetime
from app import db
from sqlalchemy import Enum
import enum

class CommentTargetType(enum.Enum):
    PAGE = 'page'
    ATTACHMENT = 'attachment'

class Comment(db.Model):
    """评论模型"""
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    content_html = db.Column(db.Text)

    # 目标类型和ID
    target_type = db.Column(Enum(CommentTargetType), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)

    # 关联信息
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'))  # 回复评论

    # 状态
    is_deleted = db.Column(db.Boolean, default=False)
    is_edited = db.Column(db.Boolean, default=False)

    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    author = db.relationship('User', foreign_keys=[author_id], backref='comments')
    parent = db.relationship('Comment', remote_side=[id], backref='replies')
    mentions = db.relationship('CommentMention', backref='comment', lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('ix_comments_target', 'target_type', 'target_id'),
        db.Index('ix_comments_author', 'author_id'),
        db.Index('ix_comments_created', 'created_at'),
    )

    def __repr__(self):
        return f'<Comment {self.id} by {self.author.username}>'

    def get_safe_datetime(self, field_name):
        """安全地获取datetime字段，处理可能的字符串类型"""
        field_value = getattr(self, field_name, None)
        if field_value is None:
            return None

        # 如果已经是datetime对象，直接返回
        if hasattr(field_value, 'strftime'):
            return field_value

        # 如果是字符串，尝试解析
        if isinstance(field_value, str):
            try:
                # 处理ISO格式字符串
                if field_value.endswith('Z'):
                    field_value = field_value[:-1] + '+00:00'
                dt = datetime.fromisoformat(field_value)
                # 移除时区信息以便使用
                if dt.tzinfo:
                    return dt.replace(tzinfo=None)
                return dt
            except (ValueError, AttributeError):
                return None

        return None

    @staticmethod
    def on_changed_content(target, value, oldvalue, initiator):
        """内容变更时处理HTML和@提及"""
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br',
                        'div', 'span', 'table', 'thead', 'tbody', 'tr', 'th', 'td']
        allowed_attrs = {'a': ['href', 'title'], 'abbr': ['title'], 'acronym': ['title']}

        # 处理@提及
        value = Comment.process_mentions(target, value)

        # 清理HTML
        from bleach import linkify, clean
        html = linkify(clean(value, tags=allowed_tags, attributes=allowed_attrs, strip=True))
        target.content_html = html

    @staticmethod
    def process_mentions(comment, content):
        """处理@提及并创建提及记录"""
        import re
        from app.models.user import User

        # 匹配@username格式
        mention_pattern = r'@(\w+)'
        mentions = re.findall(mention_pattern, content)

        for username in mentions:
            # 查找用户
            user = User.query.filter_by(username=username).first()
            if user and user.id != comment.author_id:
                # 检查是否已经提及过
                existing_mention = CommentMention.query.filter_by(
                    comment_id=comment.id,
                    mentioned_user_id=user.id
                ).first()

                if not existing_mention:
                    # 创建提及记录（只有在comment已经有ID时才创建）
                    if comment.id:
                        mention = CommentMention(
                            comment_id=comment.id,
                            mentioned_user_id=user.id,
                            mentioned_username=username
                        )
                        db.session.add(mention)

        return content

    def create_mentions_after_save(self, content):
        """在保存后创建提及记录"""
        import re
        from app.models.user import User

        # 匹配@username格式
        mention_pattern = r'@(\w+)'
        mentions = re.findall(mention_pattern, content)

        for username in mentions:
            # 查找用户
            user = User.query.filter_by(username=username).first()
            if user and user.id != self.author_id:
                # 检查是否已经提及过
                existing_mention = CommentMention.query.filter_by(
                    comment_id=self.id,
                    mentioned_user_id=user.id
                ).first()

                if not existing_mention:
                    # 创建提及记录
                    mention = CommentMention(
                        comment_id=self.id,
                        mentioned_user_id=user.id,
                        mentioned_username=username
                    )
                    db.session.add(mention)

        db.session.commit()

    def get_mentions(self):
        """获取所有被提及的用户"""
        return [mention.mentioned_user for mention in self.mentions if mention.mentioned_user]

    def to_dict(self, include_replies=False):
        """转换为字典格式"""
        # 安全地获取时间戳
        created_at = self.get_safe_datetime('created_at')
        updated_at = self.get_safe_datetime('updated_at')

        data = {
            'id': self.id,
            'content': self.content,
            'content_html': self.content_html,
            'target_type': self.target_type.value,
            'target_id': self.target_id,
            'author': {
                'id': self.author.id,
                'username': self.author.username,
                'name': self.author.name,
                'avatar': self.author.get_avatar(size=40) or '/static/img/default-avatar.png'
            },
            'parent_id': self.parent_id,
            'is_edited': self.is_edited,
            'created_at': created_at.isoformat() if created_at else None,
            'updated_at': updated_at.isoformat() if updated_at else None,
            'mentions': [
                {
                    'id': mention.mentioned_user.id,
                    'username': mention.mentioned_user.username,
                    'name': mention.mentioned_user.name
                } for mention in self.mentions if mention.mentioned_user
            ]
        }

        if include_replies:
            data['replies'] = [reply.to_dict() for reply in self.replies if not reply.is_deleted]

        return data

class CommentMention(db.Model):
    """评论提及记录"""
    __tablename__ = 'comment_mentions'

    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=False)
    mentioned_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    mentioned_username = db.Column(db.String(64), nullable=False)

    # 是否已读
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)

    # 通知状态
    notification_sent = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    mentioned_user = db.relationship('User', foreign_keys=[mentioned_user_id], backref='comment_mentions')

    __table_args__ = (
        db.Index('ix_comment_mentions_user', 'mentioned_user_id', 'is_read'),
        db.Index('ix_comment_mentions_comment', 'comment_id'),
    )

    def __repr__(self):
        return f'<CommentMention {self.mentioned_username} in comment {self.comment_id}>'

    def mark_as_read(self):
        """标记为已读"""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()
            db.session.add(self)

# 注册事件监听器
from sqlalchemy import event

@event.listens_for(Comment.content, 'set')
def on_comment_content_change(target, value, oldvalue, initiator):
    """评论内容变更时触发处理"""
    Comment.on_changed_content(target, value, oldvalue, initiator)
    target.updated_at = datetime.utcnow()

    # 如果内容有变化且不是新创建的，标记为已编辑
    if target.id and value != oldvalue:
        target.is_edited = True