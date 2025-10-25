from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from datetime import datetime
from config.config import config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
mail = Mail()
csrf = CSRFProtect()

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    csrf.init_app(app)

    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # Global context processor
    @app.context_processor
    def inject_permissions():
        from app.models.user import Permission
        return dict(Permission=Permission)

    # Custom filters
    @app.template_filter('timeago')
    def timeago(dt):
        """Convert datetime to human readable 'time ago' format"""
        if dt is None:
            return "Never"

        # 安全地处理datetime对象
        if hasattr(dt, 'strftime'):
            # 如果是datetime对象，直接使用
            datetime_obj = dt
        elif isinstance(dt, str):
            # 如果是字符串，尝试解析
            try:
                if dt.endswith('Z'):
                    dt = dt[:-1] + '+00:00'
                datetime_obj = datetime.fromisoformat(dt)
                # 移除时区信息以便比较
                if datetime_obj.tzinfo:
                    datetime_obj = datetime_obj.replace(tzinfo=None)
            except (ValueError, AttributeError):
                return "Unknown time"
        else:
            return "Unknown time"

        try:
            now = datetime.utcnow()
            diff = now - datetime_obj

            if diff.days > 365:
                years = diff.days // 365
                return f"{years} year{'s' if years != 1 else ''} ago"
            elif diff.days > 30:
                months = diff.days // 30
                return f"{months} month{'s' if months != 1 else ''} ago"
            elif diff.days > 0:
                return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            else:
                return "Just now"
        except Exception as e:
            # 如果时间计算出错，返回默认值
            return "Some time ago"

    # Register blueprints
    from app.views.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from app.views.wiki import wiki as wiki_blueprint
    app.register_blueprint(wiki_blueprint)

    from app.views.admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    from app.views.api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api')

    from app.views.watch import watch as watch_blueprint
    app.register_blueprint(watch_blueprint)

    from app.views.comment import comment as comment_blueprint
    app.register_blueprint(comment_blueprint)

    from app.views.user import user as user_blueprint
    app.register_blueprint(user_blueprint)

    from app.views.fastgpt_api import fastgpt_api as fastgpt_blueprint
    app.register_blueprint(fastgpt_blueprint)

    # CSRF exemptions for API endpoints
    @csrf.exempt
    def csrf_exempt_register():
        pass

    # Exempt specific API routes from CSRF
    csrf.exempt(api_blueprint)
    csrf.exempt(comment_blueprint)
    csrf.exempt(fastgpt_blueprint)  # Exempt FastGPT API from CSRF
    # Exempt only specific user API routes from CSRF
    from app.views import user as user_views
    csrf.exempt(user_views.update_avatar)  # Exempt only the avatar update endpoint

    # Error handlers
    @app.errorhandler(403)
    def forbidden(error):
        from flask import render_template
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(error):
        from flask import render_template
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Security headers
    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    # Process watch events after each request
    @app.teardown_request
    def process_watch_events(exception):
        """在每个请求处理完成后处理watch事件"""
        try:
            from app.services.watch_service import process_pending_watch_events
            notifications_count = process_pending_watch_events()
            if notifications_count > 0:
                print(f"Processed {notifications_count} watch notifications")
        except Exception as e:
            print(f"Error in teardown watch event processing: {e}")

    return app