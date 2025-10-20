import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime
from flask import current_app, request
import hashlib
import json

def setup_logging(app):
    """Setup application logging"""
    if not app.debug and not app.testing:
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.mkdir('logs')

        # Setup file handler
        file_handler = RotatingFileHandler('logs/enterprise_wiki.log', maxBytes=10240000, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Enterprise Wiki startup')

def log_user_activity(action, details=None):
    """Log user activity for audit trail"""
    try:
        from flask_login import current_user

        activity = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': getattr(current_user, 'id', None) if current_user else None,
            'username': getattr(current_user, 'username', None) if current_user else 'Anonymous',
            'ip_address': request.remote_addr,
            'action': action,
            'details': details or {},
            'user_agent': request.headers.get('User-Agent', ''),
            'endpoint': request.endpoint,
            'method': request.method
        }

        # Log to file
        current_app.logger.info(f"User Activity: {json.dumps(activity)}")

        # Store in Redis for recent activity (if available)
        try:
            import redis
            redis_client = redis.from_url(current_app.config.get('RATELIMIT_STORAGE_URL', 'redis://localhost:6379/0'))
            redis_client.lpush('user_activities', json.dumps(activity))
            redis_client.ltrim('user_activities', 0, 999)  # Keep last 1000 activities
            redis_client.expire('user_activities', 86400 * 7)  # Keep for 7 days
        except Exception:
            pass  # Redis not available, continue with file logging only

    except Exception as e:
        current_app.logger.error(f"Error logging user activity: {str(e)}")

def generate_etag(content):
    """Generate ETag for content"""
    return hashlib.md5(str(content).encode()).hexdigest()

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024.0 and i < len(size_name) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.1f}{size_name[i]}"

def sanitize_search_query(query):
    """Sanitize search query to prevent injection"""
    if not query:
        return ""
    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&', '|', ';', '`', '$', '(', ')', '{', '}']
    for char in dangerous_chars:
        query = query.replace(char, '')
    return query.strip()

def validate_page_slug(slug):
    """Validate page slug format"""
    import re
    if not slug:
        return False
    # Only allow alphanumeric, hyphens, and underscores
    pattern = r'^[a-zA-Z0-9_-]+$'
    return re.match(pattern, slug) is not None

def get_client_ip():
    """Get client IP address considering proxies"""
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0]
    elif request.headers.get("X-Real-IP"):
        ip = request.headers.get("X-Real-IP")
    else:
        ip = request.remote_addr
    return ip

def is_bot_request():
    """Check if request is from a bot"""
    user_agent = request.headers.get('User-Agent', '').lower()
    bot_indicators = ['bot', 'crawler', 'spider', 'scraper', 'curl', 'wget', 'python']
    return any(indicator in user_agent for indicator in bot_indicators)

def cache_key(*args, **kwargs):
    """Generate cache key for function"""
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
    return hashlib.md5(':'.join(key_parts).encode()).hexdigest()

def paginate_query(query, page, per_page, max_per_page=100):
    """Helper for query pagination"""
    per_page = min(per_page, max_per_page)
    return query.paginate(page=page, per_page=per_page, error_out=False)

def handle_file_upload(file, allowed_extensions=None, max_size=16*1024*1024):
    """Handle file upload with validation"""
    if not file or file.filename == '':
        return None, "No file selected"

    if allowed_extensions is None:
        allowed_extensions = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}

    # Check file extension
    if not ('.' in file.filename and
            file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
        return None, "File type not allowed"

    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > max_size:
        return None, f"File too large. Maximum size is {format_file_size(max_size)}"

    return file, None

def create_backup():
    """Create database backup"""
    try:
        import sqlite3
        import shutil
        from datetime import datetime

        db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        if not os.path.exists(db_path):
            return None, "Database file not found"

        # Create backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"backup_{timestamp}.db"
        backup_path = os.path.join('backups', backup_filename)

        # Create backups directory if it doesn't exist
        os.makedirs('backups', exist_ok=True)

        # Copy database file
        shutil.copy2(db_path, backup_path)

        return backup_path, None

    except Exception as e:
        return None, str(e)

def check_system_health():
    """Check system health status"""
    health = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'checks': {}
    }

    try:
        # Check database connection
        from app import db
        db.session.execute('SELECT 1')
        health['checks']['database'] = {'status': 'healthy', 'message': 'Database connection OK'}
    except Exception as e:
        health['checks']['database'] = {'status': 'unhealthy', 'message': str(e)}
        health['status'] = 'unhealthy'

    try:
        # Check Redis connection (if configured)
        import redis
        redis_client = redis.from_url(current_app.config.get('RATELIMIT_STORAGE_URL', 'redis://localhost:6379/0'))
        redis_client.ping()
        health['checks']['redis'] = {'status': 'healthy', 'message': 'Redis connection OK'}
    except Exception as e:
        health['checks']['redis'] = {'status': 'warning', 'message': str(e)}

    # Check disk space
    try:
        stat = os.statvfs('.')
        free_space = stat.f_bavail * stat.f_frsize
        total_space = stat.f_blocks * stat.f_frsize
        used_percent = ((total_space - free_space) / total_space) * 100

        if used_percent > 90:
            health['checks']['disk'] = {'status': 'unhealthy', 'message': f'Disk usage: {used_percent:.1f}%'}
            health['status'] = 'unhealthy'
        elif used_percent > 80:
            health['checks']['disk'] = {'status': 'warning', 'message': f'Disk usage: {used_percent:.1f}%'}
        else:
            health['checks']['disk'] = {'status': 'healthy', 'message': f'Disk usage: {used_percent:.1f}%'}
    except Exception as e:
        health['checks']['disk'] = {'status': 'warning', 'message': str(e)}

    return health

def send_error_notification(error, context=None):
    """Send error notification (placeholder for email/Slack integration)"""
    try:
        error_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(error),
            'type': type(error).__name__,
            'context': context or {},
            'request': {
                'url': request.url,
                'method': request.method,
                'ip': get_client_ip(),
                'user_agent': request.headers.get('User-Agent', '')
            }
        }

        # Log error
        current_app.logger.error(f"Error Notification: {json.dumps(error_data)}")

        # Here you would integrate with email, Slack, or other notification services
        # For now, just log the error

    except Exception as e:
        current_app.logger.error(f"Error sending notification: {str(e)}")

class PerformanceMonitor:
    def __init__(self):
        self.start_time = None
        self.checkpoints = []

    def start(self):
        self.start_time = datetime.utcnow()
        self.checkpoints = []

    def checkpoint(self, name):
        if self.start_time:
            now = datetime.utcnow()
            elapsed = (now - self.start_time).total_seconds()
            self.checkpoints.append((name, elapsed))

    def get_report(self):
        if not self.start_time:
            return None

        total_time = (datetime.utcnow() - self.start_time).total_seconds()
        return {
            'start_time': self.start_time.isoformat(),
            'total_time': total_time,
            'checkpoints': self.checkpoints
        }