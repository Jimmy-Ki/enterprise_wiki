from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db, mail
from app.models import User, Role, Page, Category, Attachment, UserSession, Permission
import os
import zipfile
import tempfile
from flask import send_file, jsonify
from werkzeug.utils import secure_filename
from app.decorators import admin_required
from app.forms.admin import UserForm, RoleForm, CategoryForm
from sqlalchemy import func, text

# 简单的备份记录类（临时解决方案）
class BackupRecord:
    def __init__(self, id, created_at, creator, file_size=None):
        self.id = id
        self.created_at = created_at
        self.creator = creator
        self.file_size = file_size
        self.file_path = None

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

    return render_template('admin/dashboard_standalone.html', stats=stats,
                         recent_pages=recent_pages, recent_users=recent_users,
                         user_growth=user_growth, page_growth=page_growth)

@admin.route('/users/create', methods=['GET', 'POST'])
def create_user():
    """Create a new user (admin only)"""
    from app.forms.admin import UserForm
    form = UserForm()

    if form.validate_on_submit():
        from app.models import User, Role
        from werkzeug.security import generate_password_hash
        from app import db
        import secrets
        import string

        # Check if username already exists
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already exists!', 'danger')
            return render_template('admin/create_user_standalone.html', form=form)

        # Check if email already exists
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already exists!', 'danger')
            return render_template('admin/create_user_standalone.html', form=form)

        # Generate random password
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))

        # Get default role if none specified
        default_role = Role.query.filter_by(default=True).first()
        role_id = form.role_id.data or (default_role.id if default_role else None)

        # Create new user
        user = User(
            username=form.username.data,
            email=form.email.data,
            name=form.name.data,
            role_id=role_id,
            is_active=form.is_active.data,
            confirmed=form.confirmed.data
        )

        # Set password using the User model's password setter
        user.password = password

        db.session.add(user)
        try:
            db.session.commit()

            # If email confirmation is required, send confirmation email
            if not user.confirmed:
                from app.email import send_email
                token = user.generate_confirmation_token()

                # Create email template content
                email_html = f'''
                <h2>Welcome to Enterprise Wiki!</h2>
                <p>Hello {user.name},</p>
                <p>Thank you for creating an account on Enterprise Wiki. Your account has been created successfully.</p>
                <p><strong>Your temporary password is:</strong></p>
                <p style="background-color: #f0f0f0; padding: 10px; font-family: monospace; font-size: 16px;">{password}</p>
                <p>Please change your password after logging in for security reasons.</p>
                <p><a href="{url_for('auth.confirm', token=token, _external=True)}">Click here to confirm your email address</a></p>
                <p>If you did not create this account, please contact the administrator.</p>
                <p>Best regards,<br>Enterprise Wiki Team</p>
                '''

                email_text = f'''
                Welcome to Enterprise Wiki!

                Hello {user.name},

                Thank you for creating an account on Enterprise Wiki. Your account has been created successfully.

                Your temporary password is: {password}

                Please change your password after logging in for security reasons.

                Click here to confirm your email address: {url_for('auth.confirm', token=token, _external=True)}

                If you did not create this account, please contact the administrator.

                Best regards,
                Enterprise Wiki Team
                '''

                try:
                    # Use Flask-Mail to send email directly
                    from flask_mail import Message
                    msg = Message(
                        subject='Welcome to Enterprise Wiki - Your Account is Ready',
                        sender=current_app.config.get('MAIL_SENDER', 'noreply@enterprise-wiki.com'),
                        recipients=[user.email],
                        html=email_html,
                        body=email_text
                    )
                    mail.send(msg)
                    flash(f'User created successfully! Temporary password: {password}', 'success')
                except Exception as e:
                    # If email sending fails, still show success message but note the email issue
                    flash(f'User created successfully! Temporary password: {password}', 'warning')
                    flash(f'Note: Email delivery failed - {str(e)}', 'warning')
            else:
                flash(f'User created successfully! Temporary password: {password}', 'success')

            return redirect(url_for('admin.users'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user: {str(e)}', 'danger')

    return render_template('admin/create_user_standalone.html', form=form)

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

    return render_template('admin/users_standalone.html', users=users, roles=roles,
                         role_filter=role_filter, status_filter=status_filter)

@admin.route('/users/<int:user_id>')
def user_detail(user_id):
    """User detail page"""
    user = User.query.get_or_404(user_id)
    user_pages = Page.query.filter_by(author_id=user_id)\
                          .order_by(Page.updated_at.desc()).limit(10).all()
    user_sessions = UserSession.query.filter_by(user_id=user_id)\
                                   .order_by(UserSession.created_at.desc()).limit(10).all()

    return render_template('admin/user_detail_standalone.html', user=user,
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

    return render_template('admin/edit_user_standalone.html', form=form, user=user)

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
    return render_template('admin/roles_standalone.html', roles=roles, form=form)

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
@login_required
@admin_required
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

        # 更新组织和领导信息
        from app.models.organization import Department, User
        department_id = request.form.get('department_id')
        leader_id = request.form.get('leader_id')
        role_type = request.form.get('role_type', 'general')
        description = request.form.get('description', '')

        role.department_id = int(department_id) if department_id else None
        role.leader_id = int(leader_id) if leader_id else None
        role.role_type = role_type
        role.description = description

        db.session.commit()
        flash('角色更新成功!', 'success')
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

    # 获取部门和用户列表
    from app.models.organization import Department
    departments = Department.query.filter_by(is_active=True).order_by(Department.sort_order, Department.name).all()
    users = User.query.filter_by(is_active=True).order_by(User.name).all()

    return render_template('admin/edit_role.html', form=form, role=role, departments=departments, users=users)

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
    return render_template('admin/categories_standalone.html', categories=categories)

@admin.route('/categories/create', methods=['GET', 'POST'])
def create_category():
    """Create category"""
    form = CategoryForm()
    form.parent_id.choices = [(0, 'No Parent')] + [(c.id, c.name) for c in Category.query.all()]

    if form.validate_on_submit():
        # Check if category name already exists
        existing_category = Category.query.filter_by(name=form.name.data).first()
        if existing_category:
            flash(f'Category name "{form.name.data}" already exists! Please choose a different name.', 'danger')
            return render_template('admin/create_category.html', form=form)

        category = Category(
            name=form.name.data,
            description=form.description.data,
            parent_id=form.parent_id.data if form.parent_id.data != 0 else None,
            is_public=form.is_public.data,
            created_by=current_user.id
        )

        try:
            db.session.add(category)
            db.session.commit()
            flash('Category created successfully!', 'success')
            return redirect(url_for('admin.categories'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating category: {str(e)}', 'danger')

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

        # Check if category name already exists (excluding current category)
        existing_category = Category.query.filter(
            Category.name == form.name.data,
            Category.id != category.id
        ).first()
        if existing_category:
            flash(f'Category name "{form.name.data}" already exists! Please choose a different name.', 'danger')
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

@admin.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_category(category_id):
    """Delete category"""
    category = Category.query.get_or_404(category_id)

    # Check if category has pages
    if category.pages.count() > 0:
        flash('Cannot delete category with pages. Please move or delete the pages first.', 'danger')
        return redirect(url_for('admin.categories'))

    # Check if category has children
    if category.children:
        flash('Cannot delete category with subcategories. Please delete or move subcategories first.', 'danger')
        return redirect(url_for('admin.categories'))

    try:
        db.session.delete(category)
        db.session.commit()
        flash('Category deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting category: {str(e)}', 'danger')

    return redirect(url_for('admin.categories'))

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

    return render_template('admin/pages_standalone.html', pages=pages, authors=authors,
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

    return render_template('admin/sessions_standalone.html', sessions=sessions)

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
    return render_template('admin/settings_standalone.html', config=current_app.config)

# 全局备份记录存储（临时解决方案）
backup_records = []

@admin.route('/backup')
@login_required
@admin_required
def backup():
    """Database backup"""
    # 获取系统统计信息
    user_count = User.query.count()
    page_count = Page.query.count()
    category_count = Category.query.count()
    session_count = UserSession.query.filter_by(is_active=True).count()

    return render_template('admin/backup_standalone.html',
                         backup_history=backup_records,
                         user_count=user_count,
                         page_count=page_count,
                         category_count=category_count,
                         session_count=session_count)

@admin.route('/backup/create', methods=['POST'])
@login_required
@admin_required
def create_backup():
    """Create database backup"""
    try:
        # 创建备份记录
        backup_record = BackupRecord(
            id=len(backup_records) + 1,
            created_at=datetime.utcnow(),
            creator=current_user
        )

        # 创建临时ZIP文件
        temp_dir = tempfile.mkdtemp()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'enterprise_backup_{timestamp}.zip'
        backup_path = os.path.join(temp_dir, backup_filename)

        # 创建ZIP文件
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 获取数据库路径
            database_path = current_app.config.get('DATABASE_PATH', 'instance/wiki.db')

            if os.path.exists(database_path):
                # 添加数据库文件到ZIP
                zipf.write(database_path, os.path.basename(database_path))

            # 创建数据库导出SQL文件
            sql_filename = f'database_export_{timestamp}.sql'
            sql_path = os.path.join(temp_dir, sql_filename)

            # 导出数据库为SQL语句
            with open(sql_path, 'w', encoding='utf-8') as sql_file:
                sql_file.write('-- Enterprise Wiki Database Backup\n')
                sql_file.write(f'-- Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
                sql_file.write(f'-- Backup ID: {backup_record.id}\n\n')

                # 获取所有表并生成SQL
                inspector = db.inspect(db.engine)
                for table_name in inspector.get_table_names():
                    sql_file.write(f'-- Table: {table_name}\n')

                    # 获取表结构
                    columns = inspector.get_columns(table_name)
                    create_sql = f'CREATE TABLE IF NOT EXISTS {table_name} (\n'
                    column_defs = []
                    for col in columns:
                        col_def = f'    {col["name"]} {col["type"]}'
                        if not col.get("nullable", True):
                            col_def += " NOT NULL"
                        if col.get("default") is not None:
                            col_def += f" DEFAULT {col['default']}"
                        column_defs.append(col_def)
                    create_sql += ',\n'.join(column_defs) + '\n);'
                    sql_file.write(create_sql + '\n\n')

                    # 获取表数据
                    result = db.session.execute(text(f'SELECT * FROM {table_name}'))
                    rows = result.fetchall()

                    if rows:
                        columns_list = [col["name"] for col in columns]
                        sql_file.write(f'-- Data for {table_name}\n')
                        for row in rows:
                            values = []
                            for value in row:
                                if value is None:
                                    values.append('NULL')
                                elif isinstance(value, str):
                                    escaped_value = value.replace("'", "''")
                                    values.append(f"'{escaped_value}'")
                                else:
                                    values.append(str(value))
                            insert_sql = f'INSERT INTO {table_name} ({", ".join(columns_list)}) VALUES ({", ".join(values)});'
                            sql_file.write(insert_sql + '\n')
                        sql_file.write('\n')

                sql_file.write('-- End of backup\n')

            # 添加SQL文件到ZIP
            zipf.write(sql_path, sql_filename)

            # 添加备份信息文件
            info_filename = f'backup_info_{timestamp}.txt'
            info_path = os.path.join(temp_dir, info_filename)
            with open(info_path, 'w', encoding='utf-8') as info_file:
                info_file.write(f'Enterprise Wiki Backup Information\n')
                info_file.write(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
                info_file.write(f'Backup ID: {backup_record.id}\n')
                info_file.write(f'Created by: {current_user.username}\n\n')
                info_file.write(f'Statistics:\n')
                info_file.write(f'- Users: {User.query.count()}\n')
                info_file.write(f'- Pages: {Page.query.count()}\n')
                info_file.write(f'- Categories: {Category.query.count()}\n')
                info_file.write(f'- Active Sessions: {UserSession.query.filter_by(is_active=True).count()}\n')

            zipf.write(info_path, info_filename)

        # 获取文件大小
        file_size = os.path.getsize(backup_path)
        backup_record.file_size = f"{file_size // 1024} KB"
        backup_record.file_path = backup_path

        # 添加到备份记录
        backup_records.append(backup_record)

        flash('Backup created successfully! Download will start automatically.', 'success')
        return send_file(backup_path,
                        as_attachment=True,
                        download_name=backup_filename,
                        mimetype='application/zip')

    except Exception as e:
        flash(f'Error creating backup: {str(e)}', 'danger')
        return redirect(url_for('admin.backup'))

@admin.route('/backup/download/<int:backup_id>')
@login_required
@admin_required
def download_backup(backup_id):
    """Download existing backup"""
    try:
        # 查找备份记录
        backup_record = None
        for record in backup_records:
            if record.id == backup_id:
                backup_record = record
                break

        if not backup_record or not backup_record.file_path or not os.path.exists(backup_record.file_path):
            flash('Backup file not found.', 'danger')
            return redirect(url_for('admin.backup'))

        # 生成下载文件名
        timestamp = backup_record.created_at.strftime('%Y%m%d_%H%M%S')
        backup_filename = f'enterprise_backup_{timestamp}.zip'

        return send_file(backup_record.file_path,
                        as_attachment=True,
                        download_name=backup_filename,
                        mimetype='application/zip')

    except Exception as e:
        flash(f'Error downloading backup: {str(e)}', 'danger')
        return redirect(url_for('admin.backup'))