import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///enterprise_wiki.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Security settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = 'app/static/uploads'
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}

    # Email settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_SUBJECT_PREFIX = os.environ.get('MAIL_SUBJECT_PREFIX', '[Enterprise Wiki]')
    MAIL_SENDER = os.environ.get('MAIL_SENDER', 'Enterprise Wiki <noreply@company.com>')

    # Pagination
    POSTS_PER_PAGE = 20
    SEARCH_RESULTS_PER_PAGE = 10

    # Rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

    # Wiki settings
    WIKI_HOME_PAGE = 'Home'
    WIKI_PUBLIC_ACCESS = False  # Require authentication for all pages

    # FastGPT settings
    FASTGPT_BASE_URL = os.environ.get('FASTGPT_BASE_URL', 'http://10.0.0.229:30000/api')
    FASTGPT_API_KEY = os.environ.get('FASTGPT_API_KEY', 'fastgpt-l2xX4RECkCTUJ453oq2IXG1PbxifKVYMmyEGwdvrZplKXYz1DVv9X5iu5NxSkVkI9')
    FASTGPT_APP_ID = os.environ.get('FASTGPT_APP_ID', 'default')
    FASTGPT_TIMEOUT = int(os.environ.get('FASTGPT_TIMEOUT', '60'))  # seconds

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///enterprise_wiki_dev.db'
    SESSION_COOKIE_SECURE = False

    # QQ Mail SMTP settings for development
    MAIL_SERVER = 'smtp.qq.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'jimmyki@qq.com'
    MAIL_PASSWORD = 'kurzssokwrixeahb'  # QQ邮箱授权码
    MAIL_SUBJECT_PREFIX = '[Enterprise Wiki]'
    MAIL_SENDER = 'Enterprise Wiki <jimmyki@qq.com>'

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///enterprise_wiki.db'

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}