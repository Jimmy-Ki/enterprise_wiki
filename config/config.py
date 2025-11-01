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
    ALLOWED_EXTENSIONS = None  # Allow all file types

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

    # OAuth settings
    @staticmethod
    def get_oauth_config():
        """获取OAuth配置"""
        return {
            'ukey': {
                'client_id': os.environ.get('UKEY_CLIENT_ID'),
                'client_secret': os.environ.get('UKEY_CLIENT_SECRET'),
                'issuer': os.environ.get('UKEY_ISSUER', 'https://auth.ukey.pw/oidc'),
                'redirect_uri': os.environ.get('UKEY_REDIRECT_URI'),
                'scope': os.environ.get('UKEY_SCOPE', 'openid email profile'),
                'auto_register': os.environ.get('UKEY_AUTO_REGISTER', 'true').lower() == 'true',
                'skip_2fa': os.environ.get('UKEY_SKIP_2FA', 'true').lower() == 'true',
                'default_role': os.environ.get('UKEY_DEFAULT_ROLE', 'Viewer')
            }
        }

    @staticmethod
    def get_server_name():
        """获取服务器名称，优先使用环境变量"""
        return os.environ.get('SERVER_NAME', '127.0.0.1')

    # Storage settings
    @staticmethod
    def get_storage_config():
        storage_type = os.environ.get('STORAGE_TYPE', 'local')
        storage_config = {
            'type': storage_type,
        }

        if storage_type == 'local':
            storage_config.update({
                'upload_folder': os.environ.get('UPLOAD_FOLDER', 'app/static/uploads'),
                'base_url': os.environ.get('BASE_URL', '/static/uploads')
            })
        elif storage_type == 's3':
            # 检查必需的S3配置
            required_s3_vars = ['S3_ENDPOINT_URL', 'S3_ACCESS_KEY', 'S3_SECRET_KEY', 'S3_BUCKET_NAME']
            missing_vars = [var for var in required_s3_vars if not os.environ.get(var)]

            if missing_vars:
                raise ValueError(f"缺少必需的S3配置环境变量: {', '.join(missing_vars)}")

            storage_config.update({
                'endpoint_url': os.environ.get('S3_ENDPOINT_URL'),
                'access_key': os.environ.get('S3_ACCESS_KEY'),
                'secret_key': os.environ.get('S3_SECRET_KEY'),
                'bucket_name': os.environ.get('S3_BUCKET_NAME'),
                'region': os.environ.get('S3_REGION', 'auto'),  # auto, us-east-1, etc.
                'cdn_url': os.environ.get('S3_CDN_URL')  # 可选的CDN URL
            })

        return storage_config

    @staticmethod
    def init_app(app):
        # 动态设置存储配置
        app.config['STORAGE_CONFIG'] = Config.get_storage_config()

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///enterprise_wiki_dev.db'
    SESSION_COOKIE_SECURE = False

    # 开发环境使用生产域名配置（用于OAuth测试）
    SERVER_NAME = os.environ.get('SERVER_NAME', 'wiki.ukey.pw')
    PREFERRED_URL_SCHEME = 'https'
    FORCE_HTTPS = True

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

    # Production environment settings
    DEBUG = False
    SERVER_NAME = os.environ.get('SERVER_NAME', 'wiki.ukey.pw')
    PREFERRED_URL_SCHEME = 'https'
    FORCE_HTTPS = True

    # Enhanced security for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # Force HTTPS in production
        if app.config.get('FORCE_HTTPS'):
            app.config['SESSION_COOKIE_SECURE'] = True
            app.config['PREFERRED_URL_SCHEME'] = 'https'

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}