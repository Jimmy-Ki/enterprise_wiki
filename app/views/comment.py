from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Comment, CommentMention, CommentTargetType
from app.services.comment_service import CommentService

comment = Blueprint('comment', __name__)

@comment.route('/api/comments', methods=['POST'])
@login_required
def create_comment():
    """创建评论"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # 验证必需字段
        required_fields = ['target_type', 'target_id', 'content']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400

        # 转换目标类型
        try:
            target_type = CommentTargetType(data['target_type'])
        except ValueError:
            return jsonify({'error': 'Invalid target_type'}), 400

        # 创建评论
        comment = CommentService.create_comment(
            target_type=target_type,
            target_id=data['target_id'],
            content=data['content'].strip(),
            parent_id=data.get('parent_id')
        )

        if not comment:
            return jsonify({'error': 'Failed to create comment'}), 500

        return jsonify({
            'success': True,
            'comment': comment.to_dict(include_replies=True)
        }), 201

    except Exception as e:
        current_app.logger.error(f"Error creating comment: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@comment.route('/api/comments/<int:comment_id>', methods=['PUT'])
@login_required
def update_comment(comment_id):
    """更新评论"""
    try:
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'error': 'Content is required'}), 400

        # 更新评论
        comment = CommentService.update_comment(
            comment_id=comment_id,
            content=data['content'].strip()
        )

        if not comment:
            return jsonify({'error': 'Comment not found or no permission'}), 404

        return jsonify({
            'success': True,
            'comment': comment.to_dict()
        })

    except Exception as e:
        current_app.logger.error(f"Error updating comment: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@comment.route('/api/comments/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    """删除评论"""
    try:
        # 删除评论
        success = CommentService.delete_comment(comment_id)

        if not success:
            return jsonify({'error': 'Comment not found or no permission'}), 404

        return jsonify({'success': True})

    except Exception as e:
        current_app.logger.error(f"Error deleting comment: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@comment.route('/api/comments', methods=['GET'])
def get_comments():
    """获取评论列表"""
    try:
        # 获取查询参数
        target_type = request.args.get('target_type')
        target_id = request.args.get('target_id', type=int)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        include_replies = request.args.get('include_replies', 'true').lower() == 'true'

        if not target_type or not target_id:
            return jsonify({'error': 'target_type and target_id are required'}), 400

        # 转换目标类型
        try:
            target_type = CommentTargetType(target_type)
        except ValueError:
            return jsonify({'error': 'Invalid target_type'}), 400

        # 获取评论
        result = CommentService.get_comments(
            target_type=target_type,
            target_id=target_id,
            include_replies=include_replies,
            page=page,
            per_page=per_page
        )

        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f"Error getting comments: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@comment.route('/api/users/search', methods=['GET'])
@login_required
def search_users():
    """搜索用户（用于@提及功能）"""
    try:
        query = request.args.get('q', '').strip()
        limit = request.args.get('limit', 10, type=int)

        if not query or len(query) < 2:
            return jsonify({'users': []})

        users = CommentService.search_users(query, limit)
        return jsonify({'users': users})

    except Exception as e:
        current_app.logger.error(f"Error searching users: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@comment.route('/api/mentions', methods=['GET'])
@login_required
def get_mentions():
    """获取当前用户的@提及"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'

        result = CommentService.get_user_mentions(
            user_id=current_user.id,
            unread_only=unread_only,
            page=page,
            per_page=per_page
        )

        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f"Error getting mentions: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@comment.route('/api/mentions/<int:mention_id>/read', methods=['POST'])
@login_required
def mark_mention_as_read(mention_id):
    """标记@提及为已读"""
    try:
        success = CommentService.mark_mention_as_read(mention_id, current_user.id)

        if not success:
            return jsonify({'error': 'Mention not found'}), 404

        return jsonify({'success': True})

    except Exception as e:
        current_app.logger.error(f"Error marking mention as read: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@comment.route('/api/mentions/read-all', methods=['POST'])
@login_required
def mark_all_mentions_as_read():
    """标记所有@提及为已读"""
    try:
        # 获取所有未读提及
        unread_mentions = CommentMention.query.filter_by(
            mentioned_user_id=current_user.id,
            is_read=False
        ).all()

        count = 0
        for mention in unread_mentions:
            mention.mark_as_read()
            count += 1

        db.session.commit()

        return jsonify({'success': True, 'count': count})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error marking all mentions as read: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@comment.route('/api/comments/user/<int:user_id>', methods=['GET'])
def get_user_comments(user_id):
    """获取用户的评论列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        result = CommentService.get_user_comments(
            user_id=user_id,
            page=page,
            per_page=per_page
        )

        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f"Error getting user comments: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@comment.route('/api/comments/<int:comment_id>', methods=['GET'])
def get_comment(comment_id):
    """获取单个评论详情"""
    try:
        comment = Comment.query.get(comment_id)
        if not comment or comment.is_deleted:
            return jsonify({'error': 'Comment not found'}), 404

        return jsonify({
            'comment': comment.to_dict(include_replies=True)
        })

    except Exception as e:
        current_app.logger.error(f"Error getting comment: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@comment.route('/api/comments/preview', methods=['POST'])
@login_required
def preview_comment():
    """预览评论（渲染HTML和@提及）"""
    try:
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'error': 'Content is required'}), 400

        content = data['content']

        # 创建临时评论来处理HTML和@提及
        temp_comment = Comment(
            content=content,
            target_type=CommentTargetType.PAGE,
            target_id=0,
            author_id=current_user.id
        )

        # 处理内容
        Comment.on_changed_content(temp_comment, content, None, None)

        return jsonify({
            'html': temp_comment.content_html,
            'mentions': [
                {
                    'username': mention.mentioned_username,
                    'user_id': mention.mentioned_user_id
                }
                for mention in temp_comment.mentions
            ]
        })

    except Exception as e:
        current_app.logger.error(f"Error previewing comment: {e}")
        return jsonify({'error': 'Internal server error'}), 500