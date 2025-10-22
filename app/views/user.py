from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import User, Comment, CommentTargetType
from app.services.comment_service import CommentService

user = Blueprint('user', __name__)

@user.route('/user/<username>')
def profile(username):
    """用户主页"""
    try:
        user = User.query.filter_by(username=username).first_or_404()
        current_app.logger.info(f"Loading profile for user: {username} (ID: {user.id})")

        # 获取用户统计信息
        try:
            stats = get_user_stats(user.id)
            current_app.logger.info(f"Stats loaded for user {username}: {stats}")
        except Exception as e:
            current_app.logger.error(f"Error getting stats for user {username}: {e}")
            stats = {
                'total_comments': 0,
                'authored_pages': 0,
                'edited_pages': 0,
                'uploaded_attachments': 0,
                'received_mentions': 0,
                'unread_mentions': 0,
                'recent_comments': 0
            }

        # 获取用户的最新评论
        try:
            page = request.args.get('page', 1, type=int)
            per_page = 10

            comments_result = CommentService.get_user_comments(
                user_id=user.id,
                page=page,
                per_page=per_page
            )
            current_app.logger.info(f"Comments loaded for user {username}: {comments_result.total} total")
        except Exception as e:
            current_app.logger.error(f"Error getting comments for user {username}: {e}")
            comments_result = {
                'comments': [],
                'total': 0,
                'pages': 0,
                'current_page': 1,
                'has_prev': False,
                'has_next': False
            }

        # 获取@提及统计
        try:
            from app.models.comment import CommentMention
            mentions_count = CommentMention.query.filter_by(mentioned_user_id=user.id, is_read=False).count()
            current_app.logger.info(f"Mentions count for user {username}: {mentions_count}")
        except Exception as e:
            current_app.logger.error(f"Error getting mentions for user {username}: {e}")
            mentions_count = 0

        return render_template('user/profile.html',
                             user=user,
                             stats=stats,
                             comments=comments_result,
                             mentions_count=mentions_count,
                             current_page=page)

    except Exception as e:
        current_app.logger.error(f"Error loading profile for user {username}: {e}")
        flash('An error occurred while loading the profile.', 'danger')
        return redirect(url_for('wiki.index'))

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
        current_app.logger.info(f"Avatar update request for user: {username}")

        user = User.query.filter_by(username=username).first_or_404()
        current_app.logger.info(f"Found user: {user.username} (ID: {user.id})")

        # 检查权限
        if current_user.id != user.id and not current_user.is_administrator():
            current_app.logger.warning(f"Access denied for user {current_user.username} trying to update {username}")
            return jsonify({'error': 'Access denied'}), 403

        data = request.get_json()
        current_app.logger.info(f"Received data: {data}")

        if not data:
            current_app.logger.error("No data received")
            return jsonify({'error': 'No data received'}), 400

        if 'avatar_url' not in data:
            current_app.logger.error("avatar_url not in data")
            return jsonify({'error': 'Avatar URL is required'}), 400

        avatar_url = data['avatar_url'].strip()
        current_app.logger.info(f"Updating avatar to: {avatar_url}")

        user.avatar = avatar_url if avatar_url else None  # 如果是空字符串，设为None
        db.session.commit()

        current_app.logger.info(f"Avatar updated successfully to: {user.avatar}")

        return jsonify({
            'success': True,
            'avatar_url': user.avatar
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating avatar: {e}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Internal server error'}), 500

@user.route('/profile')
@login_required
def my_profile():
    """当前用户的profile页面"""
    return redirect(url_for('user.profile', username=current_user.username))

@user.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """编辑用户profile"""
    from app.forms.user import ProfileForm

    form = ProfileForm(obj=current_user)

    if form.validate_on_submit():
        try:
            # 更新用户信息
            current_user.name = form.name.data
            current_user.email = form.email.data

            # 如果邮箱发生变化，需要重新确认
            if form.email.data != current_user.email:
                current_user.confirmed = False
                # 发送确认邮件
                from app.email import send_email
                token = current_user.generate_confirmation_token()
                send_email(current_user.email, 'Confirm Your New Email',
                           'auth/email/confirm.html',
                           user=current_user, token=token)
                flash('Email updated. Please check your inbox for confirmation.', 'info')

            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('user.profile', username=current_user.username))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating profile: {e}")
            flash('An error occurred while updating your profile.', 'danger')

    return render_template('user/edit_profile.html', form=form)

@user.route('/profile/notifications', methods=['GET', 'POST'])
@login_required
def notification_settings():
    """通知设置页面"""
    from app.forms.user import NotificationSettingsForm

    # 获取用户当前的通知设置
    settings = current_user.get_notification_settings() or {}

    form = NotificationSettingsForm(data=settings)

    if form.validate_on_submit():
        try:
            # 保存通知设置
            notification_settings = {
                'email_notifications': form.email_notifications.data,
                'watch_notifications': form.watch_notifications.data,
                'mention_notifications': form.mention_notifications.data,
                'comment_notifications': form.comment_notifications.data,
                'daily_digest': form.daily_digest.data
            }

            current_user.set_notification_settings(notification_settings)
            db.session.commit()

            flash('Notification settings updated successfully!', 'success')
            return redirect(url_for('user.profile', username=current_user.username))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating notification settings: {e}")
            flash('An error occurred while updating your notification settings.', 'danger')

    return render_template('user/notification_settings.html', form=form)

def get_user_stats(user_id):
    """获取详细的用户统计信息"""
    try:
        from app.models.wiki import Page, PageVersion, Attachment
        from app.models.comment import CommentMention, CommentTargetType
        from datetime import datetime, timedelta

        current_app.logger.info(f"Getting stats for user ID: {user_id}")

        # ===== 基础统计 =====

        # 评论统计
        total_comments = Comment.query.filter_by(
            author_id=user_id,
            is_deleted=False
        ).count()
        current_app.logger.info(f"Total comments: {total_comments}")

        # 页面统计
        authored_pages = Page.query.filter_by(author_id=user_id).count()
        published_pages = Page.query.filter_by(author_id=user_id, is_published=True).count()
        draft_pages = authored_pages - published_pages
        current_app.logger.info(f"Pages: {authored_pages} total, {published_pages} published")

        # 编辑统计（通过版本记录）
        try:
            edited_pages = db.session.query(PageVersion).filter_by(editor_id=user_id).distinct(PageVersion.page_id).count()
        except:
            edited_pages = 0
        current_app.logger.info(f"Edited pages: {edited_pages}")

        # 附件统计
        try:
            uploaded_attachments = Attachment.query.filter_by(uploaded_by=user_id).count()
        except:
            uploaded_attachments = 0
        current_app.logger.info(f"Uploaded attachments: {uploaded_attachments}")

        # @提及统计
        try:
            received_mentions = CommentMention.query.filter_by(mentioned_user_id=user_id).count()
            unread_mentions = CommentMention.query.filter_by(
                mentioned_user_id=user_id,
                is_read=False
            ).count()
        except:
            received_mentions = 0
            unread_mentions = 0
        current_app.logger.info(f"Mentions: {received_mentions} total, {unread_mentions} unread")

        # ===== 用户创建的页面详细信息 =====
        user_pages = Page.query.filter_by(author_id=user_id).all()
        current_app.logger.info(f"Found {len(user_pages)} user pages")

        # 页面浏览量统计
        total_views = sum(page.view_count for page in user_pages)
        most_viewed_page = max(user_pages, key=lambda p: p.view_count) if user_pages else None
        current_app.logger.info(f"Total views: {total_views}")

        # 最近页面更新
        recently_updated_pages = Page.query.filter_by(author_id=user_id).order_by(Page.updated_at.desc()).limit(5).all()

        # 分类统计
        pages_with_category = [p for p in user_pages if p.category_id]
        categories_used = len(set(p.category_id for p in pages_with_category)) if pages_with_category else 0

        # 最近活动统计
        now = datetime.utcnow()

        # 30天内活动
        thirty_days_ago = now - timedelta(days=30)
        recent_comments = Comment.query.filter(
            Comment.author_id == user_id,
            Comment.is_deleted == False,
            Comment.created_at >= thirty_days_ago
        ).count()

        # 7天内活动
        seven_days_ago = now - timedelta(days=7)
        weekly_comments = Comment.query.filter(
            Comment.author_id == user_id,
            Comment.is_deleted == False,
            Comment.created_at >= seven_days_ago
        ).count()

        # 最近页面更新
        recent_page_updates = Page.query.filter_by(author_id=user_id).filter(
            Page.updated_at >= seven_days_ago
        ).count()

        # ===== 用户活动时间线 =====
        recent_activities = []

        # 最近的页面创建
        recent_pages = Page.query.filter_by(author_id=user_id).order_by(Page.created_at.desc()).limit(5).all()
        for page in recent_pages:
            recent_activities.append({
                'type': 'page_created',
                'title': page.title,
                'target': f'/wiki/{page.slug}',
                'timestamp': page.get_safe_datetime('created_at'),
                'icon': 'fa-file-plus',
                'color': 'success'
            })

        # 最近的评论
        recent_user_comments = Comment.query.filter_by(author_id=user_id, is_deleted=False).order_by(Comment.created_at.desc()).limit(5).all()
        for comment in recent_user_comments:
            target_name = "Unknown"
            target_url = "#"

            try:
                if comment.target_type == CommentTargetType.PAGE:
                    if comment.target:
                        target_name = comment.target.title
                        target_url = f'/wiki/{comment.target.slug}'
                elif comment.target_type == CommentTargetType.ATTACHMENT:
                    if comment.target:
                        target_name = comment.target.filename
                        target_url = '#'
            except Exception as e:
                current_app.logger.error(f"Error processing comment target: {e}")

            recent_activities.append({
                'type': 'comment_created',
                'title': f"Comment on {target_name}",
                'target': target_url,
                'timestamp': comment.get_safe_datetime('created_at'),
                'icon': 'fa-comment',
                'color': 'info'
            })

        # 按时间排序活动
        recent_activities.sort(key=lambda x: x['timestamp'] or datetime.min, reverse=True)

        # ===== 内容质量统计 =====
        page_content_stats = {
            'total_chars': sum(len(p.content or '') for p in user_pages),
            'avg_chars': sum(len(p.content or '') for p in user_pages) / len(user_pages) if user_pages else 0,
            'longest_page': max(user_pages, key=lambda p: len(p.content or '')) if user_pages else None,
            'shortest_page': min(user_pages, key=lambda p: len(p.content or '')) if user_pages else None
        }

        # 获取用户信息
        user = User.query.get(user_id)
        account_age_days = 0
        if user and user.get_safe_datetime('member_since'):
            account_age_days = (now - user.get_safe_datetime('member_since')).days

        return {
            # 基础统计
            'total_comments': total_comments,
            'authored_pages': authored_pages,
            'published_pages': published_pages,
            'draft_pages': draft_pages,
            'edited_pages': edited_pages,
            'uploaded_attachments': uploaded_attachments,
            'received_mentions': received_mentions,
            'unread_mentions': unread_mentions,
            'recent_comments': recent_comments,
            'weekly_comments': weekly_comments,
            'recent_page_updates': recent_page_updates,

            # 内容统计
            'total_views': total_views,
            'most_viewed_page': {
                'title': most_viewed_page.title,
                'views': most_viewed_page.view_count,
                'url': f'/wiki/{most_viewed_page.slug}'
            } if most_viewed_page else None,
            'categories_used': categories_used,
            'pages_with_category': len(pages_with_category),

            # 内容质量
            'content_stats': page_content_stats,

            # 活动数据
            'recently_updated_pages': [
                {
                    'title': page.title,
                    'url': f'/wiki/{page.slug}',
                    'updated_at': page.get_safe_datetime('updated_at'),
                    'view_count': page.view_count,
                    'is_published': page.is_published
                } for page in recently_updated_pages
            ],

            'recent_activities': recent_activities[:10],  # 限制数量

            # 账户信息
            'account_age_days': account_age_days
        }

    except Exception as e:
        current_app.logger.error(f"Error getting detailed user stats: {e}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")

        # 返回基础统计
        return {
            'total_comments': 0, 'authored_pages': 0, 'published_pages': 0, 'draft_pages': 0,
            'edited_pages': 0, 'uploaded_attachments': 0, 'received_mentions': 0,
            'unread_mentions': 0, 'recent_comments': 0, 'weekly_comments': 0,
            'recent_page_updates': 0, 'total_views': 0, 'categories_used': 0,
            'content_stats': {'total_chars': 0, 'avg_chars': 0},
            'recently_updated_pages': [], 'recent_activities': []
        }