"""
S3分享文件模型
"""

from datetime import datetime, timedelta
from app import db
import uuid


class S3Share(db.Model):
    """S3分享文件模型"""
    __tablename__ = 's3_shares'

    id = db.Column(db.Integer, primary_key=True)

    # 分享信息
    share_code = db.Column(db.String(32), unique=True, nullable=False, index=True)  # 分享代码
    share_token = db.Column(db.String(64), unique=True, nullable=False, index=True)  # 分享令牌

    # 文件信息
    original_filename = db.Column(db.String(255), nullable=False)  # 原始文件名
    file_path = db.Column(db.String(500), nullable=False)  # S3文件路径
    file_size = db.Column(db.Integer, nullable=False)  # 文件大小（字节）
    file_type = db.Column(db.String(100), nullable=False)  # 文件MIME类型
    file_extension = db.Column(db.String(10), nullable=False)  # 文件扩展名

    # S3 URL信息
    s3_url = db.Column(db.String(1000), nullable=False)  # S3原始URL
    public_url = db.Column(db.String(1000), nullable=True)  # 公开访问URL（如果有的话）

    # 分享设置
    is_public = db.Column(db.Boolean, default=True, nullable=False)  # 是否公开分享
    expires_at = db.Column(db.DateTime, nullable=True)  # 过期时间
    download_count = db.Column(db.Integer, default=0, nullable=False)  # 下载次数
    max_downloads = db.Column(db.Integer, nullable=True)  # 最大下载次数限制

    # 用户信息
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    uploader = db.relationship('User', backref=db.backref('s3_shares', lazy='dynamic'))

    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_accessed_at = db.Column(db.DateTime, nullable=True)  # 最后访问时间

    # 状态
    is_active = db.Column(db.Boolean, default=True, nullable=False)  # 是否激活

    def __repr__(self):
        return f'<S3Share {self.original_filename}>'

    @property
    def is_expired(self):
        """检查是否已过期"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def is_download_limit_reached(self):
        """检查是否达到下载限制"""
        if self.max_downloads is None:
            return False
        return self.download_count >= self.max_downloads

    @property
    def can_access(self):
        """检查是否可以访问"""
        return self.is_active and not self.is_expired and not self.is_download_limit_reached

    @property
    def file_size_display(self):
        """人性化文件大小显示"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024.0
        return f"{self.file_size:.1f} TB"

    @property
    def file_icon(self):
        """根据文件类型返回图标"""
        if self.file_type.startswith('image/'):
            return 'fas fa-image'
        elif self.file_type.startswith('video/'):
            return 'fas fa-video'
        elif self.file_type.startswith('audio/'):
            return 'fas fa-music'
        elif 'pdf' in self.file_type:
            return 'fas fa-file-pdf'
        elif 'word' in self.file_type or 'document' in self.file_type:
            return 'fas fa-file-word'
        elif 'excel' in self.file_type or 'spreadsheet' in self.file_type:
            return 'fas fa-file-excel'
        elif 'powerpoint' in self.file_type or 'presentation' in self.file_type:
            return 'fas fa-file-powerpoint'
        elif 'zip' in self.file_type or 'rar' in self.file_type:
            return 'fas fa-file-archive'
        elif 'text' in self.file_type:
            return 'fas fa-file-alt'
        else:
            return 'fas fa-file'

    def increment_download_count(self):
        """增加下载次数"""
        self.download_count += 1
        self.last_accessed_at = datetime.utcnow()
        db.session.commit()

    def generate_share_codes(self):
        """生成分享代码和令牌"""
        # 生成分享代码（简短，用于URL）
        self.share_code = self._generate_share_code()

        # 生成分享令牌（长，用于安全验证）
        self.share_token = str(uuid.uuid4()).replace('-', '')

        db.session.commit()

    def _generate_share_code(self):
        """生成短分享代码"""
        while True:
            # 生成6位随机字符
            code = ''.join([
                random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
                for _ in range(6)
            ])

            # 检查是否已存在
            if not S3Share.query.filter_by(share_code=code).first():
                return code

    @staticmethod
    def find_by_share_code(share_code):
        """通过分享代码查找分享"""
        return S3Share.query.filter_by(share_code=share_code, is_active=True).first()

    @staticmethod
    def find_by_share_token(share_token):
        """通过分享令牌查找分享"""
        return S3Share.query.filter_by(share_token=share_token, is_active=True).first()

    def get_share_url(self):
        """获取分享URL"""
        return f"/share/{self.share_code}"

    def extend_expiry(self, days=30):
        """延长过期时间"""
        if self.expires_at:
            self.expires_at = max(self.expires_at, datetime.utcnow() + timedelta(days=days))
        else:
            self.expires_at = datetime.utcnow() + timedelta(days=days)
        db.session.commit()

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'share_code': self.share_code,
            'share_token': self.share_token,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'file_size_display': self.file_size_display,
            'file_type': self.file_type,
            'file_extension': self.file_extension,
            's3_url': self.s3_url,
            'public_url': self.public_url,
            'is_public': self.is_public,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'download_count': self.download_count,
            'max_downloads': self.max_downloads,
            'uploader': self.uploader.username if self.uploader else None,
            'created_at': self.created_at.isoformat(),
            'last_accessed_at': self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            'is_active': self.is_active,
            'can_access': self.can_access,
            'is_expired': self.is_expired,
            'is_download_limit_reached': self.is_download_limit_reached,
            'share_url': self.get_share_url(),
            'file_icon': self.file_icon
        }


import random