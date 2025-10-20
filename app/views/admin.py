from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from app.models import User, Role, Page, Category, Attachment, UserSession, Permission
from app.decorators import admin_required
from app.forms.admin import UserForm, RoleForm, CategoryForm
from sqlalchemy import func

admin = Blueprint('admin', __name__)

@admin.before_request
@login_required
@admin_required
def before_request():
    pass

@admin.route('/')
def dashboard():
    """Admin dashboard"""
    # Statistics
    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'total_pages': Page.query.count(),
        'published_pages': Page.query.filter_by(is_published=True).count(),
        'total_categories': Category.query.count(),
        'total_attachments': Attachment.query.count(),
        'active_sessions': UserSession.query.filter_by(is_active=True).count()
    }

    # Recent activity
    recent_pages = Page.query.order_by(Page.updated_at.desc()).limit(5).all()
    recent_users = User.query.order_by(User.member_since.desc()).limit(5).all()

    # User growth (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    user_growth_raw = db.session.query(
        func.date(User.member_since).label('date'),
        func.count(User.id).label('count')
    ).filter(User.member_since >= thirty_days_ago)\
     .group_by(func.date(User.member_since))\
     .order_by(func.date(User.member_since)).all()

    # Convert to serializable format
    user_growth = [{'date': str(row.date), 'count': row.count} for row in user_growth_raw]

    # Page creation trends
    page_growth_raw = db.session.query(
        func.date(Page.created_at).label('date'),
        func.count(Page.id).label('count')
    ).filter(Page.created_at >= thirty_days_ago)\
     .group_by(func.date(Page.created_at))\
     .order_by(func.date(Page.created_at)).all()

    page_growth = [{'date': str(row.date), 'count': row.count} for row in page_growth_raw]

    return render_template('admin/dashboard.html', stats=stats,
                         recent_pages=recent_pages, recent_users=recent_users,
                         user_growth=user_growth, page_growth=page_growth)

@admin.route('/users')
def users():
    """User management"""
    page = request.args.get('page', 1, type=int)
    role_filter = request.args.get('role', '', type=str)
    status_filter = request.args.get('status', '', type=str)

    query = User.query

    if role_filter:
        query = query.join(Role).filter(Role.name == role_filter)

    if status_filter == 'active':
        query = query.filter(User.is_active == True)
    elif status_filter == 'inactive':
        query = query.filter(User.is_active == False)
    elif status_filter == 'unconfirmed':
        query = query.filter(User.confirmed == False)

    users = query.order_by(User.member_since.desc())\
                 .paginate(page=page, per_page=20, error_out=False)

    roles = Role.query.all()

    return render_template('admin/users.html', users=users, roles=roles,
                         role_filter=role_filter, status_filter=status_filter)

@admin.route('/users/<int:user_id>')
def user_detail(user_id):
    """User detail page"""
    user = User.query.get_or_404(user_id)
    user_pages = Page.query.filter_by(author_id=user_id)\
                          .order_by(Page.updated_at.desc()).limit(10).all()
    user_sessions = UserSession.query.filter_by(user_id=user_id)\
                                   .order_by(UserSession.created_at.desc()).limit(10).all()

    return render_template('admin/user_detail.html', user=user,
                         user_pages=user_pages, user_sessions=user_sessions)

@admin.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
def edit_user(user_id):
    """Edit user"""
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    form.role_id.choices = [(r.id, r.name) for r in Role.query.all()]

    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.name = form.name.data
        user.role_id = form.role_id.data
        user.is_active = form.is_active.data
        user.confirmed = form.confirmed.data

        if form.password.data:
            user.password = form.password.data

        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/edit_user.html', form=form, user=user)

@admin.route('/users/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    """Delete user"""
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash('You cannot delete your own account!', 'danger')
        return redirect(url_for('admin.users'))

    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin.users'))

@admin.route('/users/<int:user_id>/toggle_status', methods=['POST'])
def toggle_user_status(user_id):
    """Toggle user active status"""
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash('You cannot deactivate your own account!', 'danger')
        return redirect(url_for('admin.users'))

    user.is_active = not user.is_active
    db.session.commit()

    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {status} successfully!', 'success')
    return redirect(url_for('admin.users'))

@admin.route('/roles')
def roles():
    """Role management"""
    from app.forms.admin import RoleForm
    roles = Role.query.all()
    form = RoleForm()
    return render_template('admin/roles.html', roles=roles, form=form)

@admin.route('/roles/create', methods=['GET', 'POST'])
def create_role():
    """Create new role"""
    form = RoleForm()

    if form.validate_on_submit():
        role = Role(name=form.name.data)

        # Add permissions
        if form.can_follow.data:
            role.add_permission(Permission.FOLLOW)
        if form.can_comment.data:
            role.add_permission(Permission.COMMENT)
        if form.can_write.data:
            role.add_permission(Permission.WRITE)
        if form.can_moderate.data:
            role.add_permission(Permission.MODERATE)
        if form.can_view_private.data:
            role.add_permission(Permission.VIEW_PRIVATE)
        if form.can_edit_all.data:
            role.add_permission(Permission.EDIT_ALL)
        if form.can_delete_all.data:
            role.add_permission(Permission.DELETE_ALL)
        if form.is_admin.data:
            role.add_permission(Permission.ADMIN)

        db.session.add(role)
        db.session.commit()
        flash('Role created successfully!', 'success')
        return redirect(url_for('admin.roles'))

    return render_template('admin/create_role.html', form=form)

@admin.route('/roles/<int:role_id>/edit', methods=['GET', 'POST'])
def edit_role(role_id):
    """Edit role"""
    role = Role.query.get_or_404(role_id)
    form = RoleForm(obj=role)

    if form.validate_on_submit():
        role.name = form.name.data
        role.reset_permissions()

        # Add permissions
        if form.can_follow.data:
            role.add_permission(Permission.FOLLOW)
        if form.can_comment.data:
            role.add_permission(Permission.COMMENT)
        if form.can_write.data:
            role.add_permission(Permission.WRITE)
        if form.can_moderate.data:
            role.add_permission(Permission.MODERATE)
        if form.can_view_private.data:
            role.add_permission(Permission.VIEW_PRIVATE)
        if form.can_edit_all.data:
            role.add_permission(Permission.EDIT_ALL)
        if form.can_delete_all.data:
            role.add_permission(Permission.DELETE_ALL)
        if form.is_admin.data:
            role.add_permission(Permission.ADMIN)

        db.session.commit()
        flash('Role updated successfully!', 'success')
        return redirect(url_for('admin.roles'))

    # Set form values based on current permissions
    form.can_follow.data = role.has_permission(Permission.FOLLOW)
    form.can_comment.data = role.has_permission(Permission.COMMENT)
    form.can_write.data = role.has_permission(Permission.WRITE)
    form.can_moderate.data = role.has_permission(Permission.MODERATE)
    form.can_view_private.data = role.has_permission(Permission.VIEW_PRIVATE)
    form.can_edit_all.data = role.has_permission(Permission.EDIT_ALL)
    form.can_delete_all.data = role.has_permission(Permission.DELETE_ALL)
    form.is_admin.data = role.has_permission(Permission.ADMIN)

    return render_template('admin/edit_role.html', form=form, role=role)

@admin.route('/roles/<int:role_id>/delete', methods=['POST'])
def delete_role(role_id):
    """Delete role"""
    role = Role.query.get_or_404(role_id)

    # Prevent deletion of default roles
    if role.default or role.name == 'Administrator':
        flash('Cannot delete default or Administrator role!', 'danger')
        return redirect(url_for('admin.roles'))

    # Check if users are assigned to this role
    if role.users.count() > 0:
        flash('Cannot delete role with assigned users!', 'danger')
        return redirect(url_for('admin.roles'))

    db.session.delete(role)
    db.session.commit()
    flash('Role deleted successfully!', 'success')
    return redirect(url_for('admin.roles'))

@admin.route('/categories')
def categories():
    """Category management"""
    categories = Category.query.order_by(Category.name).all()
    return render_template('admin/categories.html', categories=categories)

@admin.route('/categories/create', methods=['GET', 'POST'])
def create_category():
    """Create category"""
    form = CategoryForm()
    form.parent_id.choices = [(0, 'No Parent')] + [(c.id, c.name) for c in Category.query.all()]

    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            description=form.description.data,
            parent_id=form.parent_id.data if form.parent_id.data != 0 else None,
            is_public=form.is_public.data,
            created_by=current_user.id
        )

        db.session.add(category)
        db.session.commit()
        flash('Category created successfully!', 'success')
        return redirect(url_for('admin.categories'))

    return render_template('admin/create_category.html', form=form)

@admin.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
def edit_category(category_id):
    """Edit category"""
    category = Category.query.get_or_404(category_id)
    form = CategoryForm(obj=category)
    form.parent_id.choices = [(0, 'No Parent')] + [(c.id, c.name) for c in Category.query.all() if c.id != category_id]

    if form.validate_on_submit():
        parent_id = form.parent_id.data if form.parent_id.data != 0 else None

        # Check for circular relationship
        if category.would_create_cycle(parent_id):
            flash('Circular parent-child relationship detected! This change would create an infinite loop.', 'danger')
            return render_template('admin/edit_category.html', form=form, category=category)

        category.name = form.name.data
        category.description = form.description.data
        category.parent_id = parent_id
        category.is_public = form.is_public.data

        try:
            db.session.commit()
            flash('Category updated successfully!', 'success')
            return redirect(url_for('admin.categories'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating category: {str(e)}', 'danger')

    return render_template('admin/edit_category.html', form=form, category=category)

@admin.route('/pages')
def pages():
    """Page management"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '', type=str)
    author_filter = request.args.get('author', '', type=int)

    query = Page.query

    if status_filter == 'published':
        query = query.filter_by(is_published=True)
    elif status_filter == 'draft':
        query = query.filter_by(is_published=False)

    if author_filter:
        query = query.filter_by(author_id=author_filter)

    pages = query.order_by(Page.updated_at.desc())\
                 .paginate(page=page, per_page=20, error_out=False)

    authors = db.session.query(User.id, User.username).join(Page, User.id == Page.author_id).distinct().all()

    return render_template('admin/pages.html', pages=pages, authors=authors,
                         status_filter=status_filter, author_filter=author_filter)

@admin.route('/pages/<int:page_id>/toggle_status', methods=['POST'])
def toggle_page_status(page_id):
    """Toggle page published status"""
    page = Page.query.get_or_404(page_id)
    page.is_published = not page.is_published

    if page.is_published and not page.published_at:
        page.published_at = datetime.utcnow()

    db.session.commit()

    status = 'published' if page.is_published else 'unpublished'
    flash(f'Page {status} successfully!', 'success')
    return redirect(request.referrer or url_for('admin.pages'))

@admin.route('/sessions')
def sessions():
    """Active sessions"""
    page = request.args.get('page', 1, type=int)
    sessions = UserSession.query.filter_by(is_active=True)\
                              .order_by(UserSession.created_at.desc())\
                              .paginate(page=page, per_page=50, error_out=False)

    return render_template('admin/sessions.html', sessions=sessions)

@admin.route('/sessions/<int:session_id>/revoke', methods=['POST'])
def revoke_session(session_id):
    """Revoke session"""
    session = UserSession.query.get_or_404(session_id)
    session.revoke()
    db.session.commit()
    flash('Session revoked successfully!', 'success')
    return redirect(url_for('admin.sessions'))

@admin.route('/settings')
def settings():
    """System settings"""
    return render_template('admin/settings.html')

@admin.route('/backup')
def backup():
    """Database backup"""
    # This would implement database backup functionality
    flash('Backup functionality not implemented yet!', 'info')
    return redirect(url_for('admin.dashboard'))