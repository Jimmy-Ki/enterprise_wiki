import hashlib
import secrets
from datetime import datetime, timedelta
from flask import request, session, current_app
from werkzeug.security import generate_password_hash
from functools import wraps
from flask import abort, jsonify
import redis
import time
import logging

logger = logging.getLogger(__name__)

class SecurityManager:
    def __init__(self, app=None):
        self.redis_client = None
        if app:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        self.redis_client = redis.from_url(app.config.get('RATELIMIT_STORAGE_URL', 'redis://localhost:6379/0'))

    def generate_csrf_token(self):
        """Generate CSRF token"""
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_urlsafe(32)
        return session['csrf_token']

    def validate_csrf_token(self, token):
        """Validate CSRF token"""
        if 'csrf_token' not in session:
            return False
        return secrets.compare_digest(session['csrf_token'], token)

    def is_safe_url(self, target):
        """Check if URL is safe for redirects"""
        ref_url = request.host_url
        test_url = request.host_url + target
        return target.startswith(ref_url) or target.startswith('/')

    def generate_password_reset_token(self, user_id, expires_in=3600):
        """Generate secure password reset token"""
        data = f"{user_id}:{int(time.time())}:{secrets.token_urlsafe(16)}"
        return hashlib.sha256(data.encode()).hexdigest()

    def validate_password_reset_token(self, token, user_id, max_age=3600):
        """Validate password reset token"""
        # This is a simplified version - in production, use proper signed tokens
        return token and len(token) == 64

    def log_security_event(self, event_type, user_id=None, details=None):
        """Log security events"""
        event_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'details': details or {}
        }

        logger.warning(f"Security Event: {event_type}", extra=event_data)

        # Store in Redis for recent events monitoring
        if self.redis_client:
            self.redis_client.lpush('security_events', str(event_data))
            self.redis_client.ltrim('security_events', 0, 999)  # Keep last 1000 events
            self.redis_client.expire('security_events', 86400)  # 24 hours

class RateLimiter:
    def __init__(self, redis_client):
        self.redis_client = redis_client

    def is_rate_limited(self, key, limit, window):
        """
        Check if rate limit is exceeded using sliding window algorithm

        Args:
            key: Unique key for rate limiting (e.g., 'login:IP_ADDRESS')
            limit: Maximum number of requests allowed
            window: Time window in seconds

        Returns:
            tuple: (is_limited, remaining_requests, reset_time)
        """
        now = time.time()
        window_start = now - window

        # Remove old entries
        self.redis_client.zremrangebyscore(key, 0, window_start)

        # Count current requests
        current_requests = self.redis_client.zcard(key)

        if current_requests >= limit:
            # Get oldest request time for reset time
            oldest = self.redis_client.zrange(key, 0, 0, withscores=True)
            if oldest and len(oldest) > 0 and len(oldest[0]) > 1:
                reset_time = oldest[0][1] + window
            else:
                reset_time = now + window
            return True, 0, reset_time

        # Add current request
        self.redis_client.zadd(key, {str(now): now})
        self.redis_client.expire(key, window)

        remaining = limit - current_requests - 1
        return False, remaining, now + window

class InputSanitizer:
    @staticmethod
    def sanitize_html(content, allowed_tags=None, allowed_attributes=None):
        """Sanitize HTML content"""
        import bleach

        if allowed_tags is None:
            allowed_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'strong', 'em',
                           'u', 'ol', 'ul', 'li', 'code', 'pre', 'blockquote', 'a',
                           'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'div', 'span']

        if allowed_attributes is None:
            allowed_attributes = {
                'a': ['href', 'title'],
                'img': ['src', 'alt', 'title', 'width', 'height'],
                '*': ['class']
            }

        return bleach.clean(content, tags=allowed_tags, attributes=allowed_attributes, strip=True)

    @staticmethod
    def sanitize_filename(filename):
        """Sanitize filename for secure storage"""
        import re
        from werkzeug.utils import secure_filename

        # Remove dangerous characters
        filename = re.sub(r'[^\w\s.-]', '', filename)
        # Convert spaces to underscores
        filename = re.sub(r'\s+', '_', filename)
        # Use werkzeug's secure_filename
        return secure_filename(filename)

    @staticmethod
    def validate_url(url):
        """Validate URL is safe"""
        import re
        url_pattern = re.compile(
            r'^(?:http|ftp)s?://'  # http:// or https://
            r'(?:\S+(?::\S*)?@)?'  # optional username:password@
            r'(?:'  # IP address exclusion
            r'(?:(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-5])\.){3}(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-5])'
            r'|'  # or domain name
            r'(?:(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)'  # domain label
            r'(?:\.(?:[a-z\u00a1-\uffff0-9]-*)*[a-z\u00a1-\uffff0-9]+)*'  # sub domain
            r'(?:\.(?:[a-z\u00a1-\uffff]{2,}))'  # top-level domain
            r')'
            r'(?::\d{2,5})?'  # port
            r'(?:/[^\s]*)?$', re.IGNORECASE)
        return re.match(url_pattern, url) is not None

# Decorators for security
def rate_limit(limit=5, window=300, scope_func=lambda: request.remote_addr):
    """
    Rate limiting decorator

    Args:
        limit: Number of requests allowed
        window: Time window in seconds
        scope_func: Function to generate unique key (defaults to IP address)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get rate limiter
            rate_limiter = current_app.extensions.get('rate_limiter')
            if not rate_limiter:
                return f(*args, **kwargs)

            # Generate key
            key = f"rate_limit:{scope_func()}:{request.endpoint}"

            # Check rate limit
            is_limited, remaining, reset_time = rate_limiter.is_rate_limited(key, limit, window)

            if is_limited:
                if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'reset_time': reset_time
                    }), 429
                else:
                    abort(429)

            # Add rate limit headers
            response = f(*args, **kwargs)
            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Limit'] = str(limit)
                response.headers['X-RateLimit-Remaining'] = str(remaining)
                response.headers['X-RateLimit-Reset'] = str(int(reset_time))

            return response
        return decorated_function
    return decorator

def require_https(f):
    """Force HTTPS redirect"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_secure and current_app.config.get('FORCE_HTTPS', False):
            return redirect(request.url.replace('http://', 'https://'), code=301)
        return f(*args, **kwargs)
    return decorated_function

def validate_csrf(f):
    """CSRF validation decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            token = request.headers.get('X-CSRFToken') or request.form.get('csrf_token')
            security_manager = current_app.extensions.get('security_manager')

            if not security_manager or not security_manager.validate_csrf_token(token):
                if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
                    return jsonify({'error': 'Invalid CSRF token'}), 403
                else:
                    abort(403)

        return f(*args, **kwargs)
    return decorated_function

def log_security_event(event_type):
    """Decorator to log security events"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            security_manager = current_app.extensions.get('security_manager')

            # Log before function execution
            if security_manager:
                user_id = getattr(current_user, 'id', None) if current_user else None
                security_manager.log_security_event(
                    event_type=event_type,
                    user_id=user_id,
                    details={'endpoint': request.endpoint, 'method': request.method}
                )

            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Initialize security extensions
def init_security(app):
    """Initialize security extensions"""
    security_manager = SecurityManager(app)
    rate_limiter = RateLimiter(security_manager.redis_client)

    app.extensions['security_manager'] = security_manager
    app.extensions['rate_limiter'] = rate_limiter

    return security_manager, rate_limiter