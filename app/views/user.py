from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import User, Comment, CommentTargetType
from app.services.comment_service import CommentService

user = Blueprint('user', __name__)

@user.route('/user/<username>')
def profile(username):
    """用户主页"""
    user = User.query.filter_by(username=username).first_or_404()

    # 获取用户统计信息
    stats = get_user_stats(user.id)

    # 获取用户的最新评论
    page = request.args.get('page', 1, type=int)
    per_page = 10

    comments_result = CommentService.get_user_comments(
        user_id=user.id,
        page=page,
        per_page=per_page
    )

    # 获取@提及统计
    from app.models.comment import CommentMention
    mentions_count = CommentMention.query.filter_by(mentioned_user_id=user.id, is_read=False).count()

    return render_template('user/profile.html',
                         user=user,
                         stats=stats,
                         comments=comments_result,
                         mentions_count=mentions_count,
                         current_page=page)

@user.route('/api/user/<username>/stats')
def user_stats(username):
    """获取用户统计信息API"""
    try:
        user = User.query.filter_by(username=username).first_or_404()
        stats = get_user_stats(user.id)
        return jsonify(stats)
    except Exception as e:
        current_app.logger.error(f"Error getting user stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@user.route('/api/user/<username>/comments')
def user_comments(username):
    """获取用户评论API"""
    try:
        user = User.query.filter_by(username=username).first_or_404()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        result = CommentService.get_user_comments(
            user_id=user.id,
            page=page,
            per_page=per_page
        )

        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"Error getting user comments: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@user.route('/api/user/<username>/mentions')
@login_required
def user_mentions(username):
    """获取用户的@提及（仅自己或管理员可见）"""
    try:
        user = User.query.filter_by(username=username).first_or_404()

        # 检查权限
        if current_user.id != user.id and not current_user.is_administrator():
            return jsonify({'error': 'Access denied'}), 403

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'

        result = CommentService.get_user_mentions(
            user_id=user.id,
            unread_only=unread_only,
            page=page,
            per_page=per_page
        )

        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"Error getting user mentions: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@user.route('/api/user/<username>/avatar', methods=['POST'])
@login_required
def update_avatar(username):
    """更新用户头像"""
    try:
        user = User.query.filter_by(username=username).first_or_404()

        # 检查权限
        if current_user.id != user.id and not current_user.is_administrator():
            return jsonify({'error': 'Access denied'}), 403

        data = request.get_json()
        if not data or 'avatar_url' not in data:
            return jsonify({'error': 'Avatar URL is required'}), 400

        user.avatar = data['avatar_url'].strip()
        db.session.commit()

        return jsonify({
            'success': True,
            'avatar_url': user.avatar
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating avatar: {e}")
        return jsonify({'error': 'Internal server error'}), 500

def get_user_stats(user_id):
    """获取用户统计信息"""
    try:
        from app.models.wiki import Page, Attachment

        # 评论统计
        total_comments = Comment.query.filter_by(
            author_id=user_id,
            is_deleted=False
        ).count()

        # 页面统计
        authored_pages = Page.query.filter_by(author_id=user_id).count()
        edited_pages = db.session.query(PageVersion).filter_by(editor_id=user_id).count()

        # 附件统计
        uploaded_attachments = Attachment.query.filter_by(uploaded_by=user_id).count()

        # @提及统计
        from app.models.comment import CommentMention
        received_mentions = CommentMention.query.filter_by(mentioned_user_id=user_id).count()
        unread_mentions = CommentMention.query.filter_by(
            mentioned_user_id=user_id,
            is_read=False
        ).count()

        # 活跃度统计
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        # 处理可能的字符串日期格式
        recent_comments_query = Comment.query.filter(
            Comment.author_id == user_id,
            Comment.is_deleted == False
        )

        recent_comments = 0
        for comment in recent_comments_query.all():
            try:
                # 尝试解析日期字符串
                if isinstance(comment.created_at, str):
                    comment_date = datetime.fromisoformat(comment.created_at.replace('Z', '+00:00'))
                else:
                    comment_date = comment.created_at

                if comment_date >= thirty_days_ago:
                    recent_comments += 1
            except (ValueError, AttributeError):
                # 如果日期解析失败，跳过此评论
                continue

        return {
            'total_comments': total_comments,
            'authored_pages': authored_pages,
            'edited_pages': edited_pages,
            'uploaded_attachments': uploaded_attachments,
            'received_mentions': received_mentions,
            'unread_mentions': unread_mentions,
            'recent_comments': recent_comments
        }
    except Exception as e:
        current_app.logger.error(f"Error getting user stats: {e}")
        return {
            'total_comments': 0,
            'authored_pages': 0,
            'edited_pages': 0,
            'uploaded_attachments': 0,
            'received_mentions': 0,
            'unread_mentions': 0,
            'recent_comments': 0
        }