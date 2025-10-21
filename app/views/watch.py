from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Watch, WatchNotification, WatchTargetType, WatchEventType
from app.services.watch_service import WatchService
from datetime import datetime

watch = Blueprint('watch', __name__)

@watch.route('/api/watch', methods=['POST'])
@login_required
def create_watch():
    """创建或更新watch"""
    data = request.get_json()

    try:
        target_type_str = data.get('target_type')
        target_id = data.get('target_id')
        events = data.get('events', [])

        # 验证目标类型
        if target_type_str not in ['page', 'category']:
            return jsonify({'error': 'Invalid target_type'}), 400

        target_type = WatchTargetType.PAGE if target_type_str == 'page' else WatchTargetType.CATEGORY

        # 验证目标是否存在
        from app.models.wiki import Page, Category
        if target_type == WatchTargetType.PAGE:
            target = Page.query.get(target_id)
            if not target:
                return jsonify({'error': 'Page not found'}), 404
        else:
            target = Category.query.get(target_id)
            if not target:
                return jsonify({'error': 'Category not found'}), 404

        # 创建或更新watch
        watch_obj = WatchService.create_watch(
            current_user.id,
            target_type,
            target_id,
            events
        )

        if watch_obj:
            return jsonify({
                'success': True,
                'watch': {
                    'id': watch_obj.id,
                    'target_type': watch_obj.target_type.value,
                    'target_id': watch_obj.target_id,
                    'events': watch_obj.get_watched_events(),
                    'is_active': watch_obj.is_active
                }
            })
        else:
            return jsonify({'error': 'Failed to create watch'}), 500

    except Exception as e:
        current_app.logger.error(f"Error creating watch: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@watch.route('/api/watch/toggle', methods=['POST'])
@login_required
def toggle_watch():
    """切换watch状态"""
    data = request.get_json()

    try:
        target_type_str = data.get('target_type')
        target_id = data.get('target_id')
        events = data.get('events', [])

        # 验证目标类型
        if target_type_str not in ['page', 'category']:
            return jsonify({'error': 'Invalid target_type'}), 400

        target_type = WatchTargetType.PAGE if target_type_str == 'page' else WatchTargetType.CATEGORY

        # 切换watch状态
        watch_obj, is_new = WatchService.toggle_watch(
            current_user.id,
            target_type,
            target_id,
            events
        )

        return jsonify({
            'success': True,
            'watch': {
                'id': watch_obj.id,
                'target_type': watch_obj.target_type.value,
                'target_id': watch_obj.target_id,
                'events': watch_obj.get_watched_events(),
                'is_active': watch_obj.is_active
            },
            'is_new': is_new
        })

    except Exception as e:
        current_app.logger.error(f"Error toggling watch: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@watch.route('/api/watch/<target_type>/<int:target_id>', methods=['DELETE'])
@login_required
def remove_watch(target_type, target_id):
    """移除watch"""
    try:
        # 验证目标类型
        if target_type not in ['page', 'category']:
            return jsonify({'error': 'Invalid target_type'}), 400

        watch_target_type = WatchTargetType.PAGE if target_type == 'page' else WatchTargetType.CATEGORY

        success = WatchService.remove_watch(current_user.id, watch_target_type, target_id)

        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Watch not found'}), 404

    except Exception as e:
        current_app.logger.error(f"Error removing watch: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@watch.route('/api/watch/<target_type>/<int:target_id>', methods=['GET'])
@login_required
def get_watch_status(target_type, target_id):
    """获取watch状态"""
    try:
        # 验证目标类型
        if target_type not in ['page', 'category']:
            return jsonify({'error': 'Invalid target_type'}), 400

        watch_target_type = WatchTargetType.PAGE if target_type == 'page' else WatchTargetType.CATEGORY

        watch_obj = Watch.query.filter_by(
            user_id=current_user.id,
            target_type=watch_target_type,
            target_id=target_id,
            is_active=True
        ).first()

        if watch_obj:
            return jsonify({
                'is_watching': True,
                'watch': {
                    'id': watch_obj.id,
                    'events': watch_obj.get_watched_events(),
                    'is_active': watch_obj.is_active
                }
            })
        else:
            return jsonify({
                'is_watching': False,
                'watch': None
            })

    except Exception as e:
        current_app.logger.error(f"Error getting watch status: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@watch.route('/api/watches', methods=['GET'])
@login_required
def get_user_watches():
    """获取用户的所有watch"""
    try:
        target_type = request.args.get('target_type')

        watches = WatchService.get_user_watches(current_user.id, target_type)

        result = []
        for watch_obj in watches:
            # 获取目标信息
            target_info = {}
            if watch_obj.target_type == WatchTargetType.PAGE:
                from app.models.wiki import Page
                page = Page.query.get(watch_obj.target_id)
                if page:
                    target_info = {
                        'title': page.title,
                        'slug': page.slug,
                        'updated_at': page.updated_at.isoformat()
                    }
            elif watch_obj.target_type == WatchTargetType.CATEGORY:
                from app.models.wiki import Category
                category = Category.query.get(watch_obj.target_id)
                if category:
                    target_info = {
                        'name': category.name,
                        'description': category.description
                    }

            result.append({
                'id': watch_obj.id,
                'target_type': watch_obj.target_type.value,
                'target_id': watch_obj.target_id,
                'target_info': target_info,
                'events': watch_obj.get_watched_events(),
                'is_active': watch_obj.is_active,
                'created_at': watch_obj.created_at.isoformat()
            })

        return jsonify({
            'success': True,
            'watches': result
        })

    except Exception as e:
        current_app.logger.error(f"Error getting user watches: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@watch.route('/api/notifications', methods=['GET'])
@login_required
def get_notifications():
    """获取用户通知"""
    try:
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 50))

        notifications = WatchService.get_user_notifications(
            current_user.id,
            unread_only,
            limit
        )

        result = [notification.to_dict() for notification in notifications]

        return jsonify({
            'success': True,
            'notifications': result,
            'unread_count': WatchService.get_unread_count(current_user.id)
        })

    except Exception as e:
        current_app.logger.error(f"Error getting notifications: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@watch.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """标记通知为已读"""
    try:
        success = WatchService.mark_notification_read(notification_id, current_user.id)

        if success:
            return jsonify({
                'success': True,
                'unread_count': WatchService.get_unread_count(current_user.id)
            })
        else:
            return jsonify({'error': 'Notification not found'}), 404

    except Exception as e:
        current_app.logger.error(f"Error marking notification as read: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@watch.route('/api/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """标记所有通知为已读"""
    try:
        count = WatchService.mark_all_notifications_read(current_user.id)

        return jsonify({
            'success': True,
            'marked_count': count,
            'unread_count': 0
        })

    except Exception as e:
        current_app.logger.error(f"Error marking all notifications as read: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@watch.route('/api/notifications/unread-count', methods=['GET'])
@login_required
def get_unread_count():
    """获取未读通知数量"""
    try:
        count = WatchService.get_unread_count(current_user.id)

        return jsonify({
            'success': True,
            'unread_count': count
        })

    except Exception as e:
        current_app.logger.error(f"Error getting unread count: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500