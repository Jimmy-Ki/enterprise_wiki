from functools import wraps
from flask import abort, request, jsonify
from flask_login import current_user
from app.models import Permission

def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.can(permission):
                if request.accept_mimetypes.accept_json and \
                   not request.accept_mimetypes.accept_html:
                    return jsonify({'error': 'Insufficient permissions'}), 403
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_administrator():
            if request.accept_mimetypes.accept_json and \
               not request.accept_mimetypes.accept_html:
                return jsonify({'error': 'Administrator access required'}), 403
            abort(403)
        return f(*args, **kwargs)
    return decorated_function