from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.models import Page, Category, Attachment, PageVersion, Permission, User
from app.decorators import permission_required
from app.forms.wiki import PageForm, CategoryForm, SearchForm
from app.services.storage_service import create_storage_service
from werkzeug.utils import secure_filename
import os
import markdown
import bleach

wiki = Blueprint('wiki', __name__)

@wiki.route('/')
def index():
    """Wiki home page with Confluence-style layout"""
    # Get home page or category listing
    home_page = Page.query.filter_by(slug=current_app.config.get('WIKI_HOME_PAGE', 'home')).first()
    if home_page and home_page.can_view(current_user):
        return render_template('wiki/page_confluence.html', page=home_page)

    # Show category listing with Confluence layout
    categories = Category.query.filter_by(parent_id=None).all()
    recent_pages = Page.query.filter_by(is_published=True)\
                           .order_by(Page.updated_at.desc()).limit(10).all()

    # Filter pages based on permissions
    accessible_pages = [page for page in recent_pages if page.can_view(current_user)]

    # Build category tree with pages
    def build_category_tree_with_pages(categories, parent_id=None):
        tree = []
        for category in categories:
            if category.parent_id == parent_id:
                # Get pages in this category
                category_pages = Page.query.filter_by(category_id=category.id, is_published=True)\
                                       .order_by(Page.title).all()
                accessible_category_pages = [page for page in category_pages if page.can_view(current_user)]

                # Get child categories
                children = build_category_tree_with_pages(categories, category.id)

                tree.append({
                    'category': category,
                    'pages': accessible_category_pages,
                    'children': children
                })
        return tree

    # Get all categories for building tree
    all_categories = Category.query.all()
    category_tree = build_category_tree_with_pages(all_categories)

    return render_template('wiki/index_confluence_static.html',
                         categories=categories,
                         recent_pages=accessible_pages,
                         category_tree=category_tree)

@wiki.route('/search')
def search():
    """Search pages"""
    form = SearchForm()
    page = request.args.get('page', 1, type=int)
    query = request.args.get('q', '').strip()

    if not query:
        # Build category tree with pages for sidebar
        def build_category_tree_with_pages(categories, parent_id=None):
            tree = []
            for category in categories:
                if category.parent_id == parent_id:
                    # Get pages in this category
                    category_pages = Page.query.filter_by(category_id=category.id, is_published=True)\
                                           .order_by(Page.title).all()
                    accessible_category_pages = [page for page in category_pages if page.can_view(current_user)]

                    # Get child categories
                    children = build_category_tree_with_pages(categories, category.id)

                    tree.append({
                        'category': category,
                        'pages': accessible_category_pages,
                        'children': children
                    })
            return tree

        # Get data for sidebar
        all_categories = Category.query.all()
        category_tree = build_category_tree_with_pages(all_categories)

        recent_pages = Page.query.filter_by(is_published=True)\
                               .order_by(Page.updated_at.desc()).limit(10).all()
        accessible_recent_pages = [page for page in recent_pages if page.can_view(current_user)]

        # Get statistics
        total_pages = Page.query.count()
        published_pages = Page.query.filter_by(is_published=True).count()
        total_categories = Category.query.count()

        return render_template('wiki/search_confluence.html', form=form, results=None, query='',
                             category_tree=category_tree, recent_pages=accessible_recent_pages,
                             total_pages=total_pages, published_pages=published_pages,
                             total_categories=total_categories)

    # Use database search (simplified version)
    pages = Page.query.filter(
        Page.is_published == True,
        Page.is_public == True,
        db.or_(
            Page.title.contains(query),
            Page.content.contains(query),
            Page.summary.contains(query)
        )
    ).paginate(page=page, per_page=10, error_out=False)

    # Filter results based on permissions
    accessible_pages = []
    for page in pages.items:
        if page.can_view(current_user):
            accessible_pages.append(page)

    # Build category tree with pages for sidebar
    def build_category_tree_with_pages(categories, parent_id=None):
        tree = []
        for category in categories:
            if category.parent_id == parent_id:
                # Get pages in this category
                category_pages = Page.query.filter_by(category_id=category.id, is_published=True)\
                                       .order_by(Page.title).all()
                accessible_category_pages = [page for page in category_pages if page.can_view(current_user)]

                # Get child categories
                children = build_category_tree_with_pages(categories, category.id)

                tree.append({
                    'category': category,
                    'pages': accessible_category_pages,
                    'children': children
                })
        return tree

    # Get data for sidebar
    all_categories = Category.query.all()
    category_tree = build_category_tree_with_pages(all_categories)

    recent_pages = Page.query.filter_by(is_published=True)\
                           .order_by(Page.updated_at.desc()).limit(10).all()
    accessible_recent_pages = [page for page in recent_pages if page.can_view(current_user)]

    # Get popular pages
    popular_pages = Page.query.filter_by(is_published=True)\
                            .order_by(Page.view_count.desc()).limit(5).all()
    accessible_popular_pages = [page for page in popular_pages if page.can_view(current_user)]

    # Get filter data
    categories = Category.query.all()
    authors = db.session.query(Page.author_id, User.username).join(User, Page.author_id == User.id).filter(Page.is_published == True).distinct().all()

    return render_template('wiki/search_confluence.html', form=form, pages=accessible_pages,
                         query=query, pagination=pages, category_tree=category_tree,
                         recent_pages=accessible_recent_pages, popular_pages=accessible_popular_pages,
                         categories=categories, authors=authors)

@wiki.route('/category/<int:category_id>')
def category_view(category_id):
    """View category and its pages"""
    category = Category.query.get_or_404(category_id)

    # Check if user can view this category
    if not category.is_public and not current_user.is_authenticated:
        abort(403)

    # Get child categories
    child_categories = Category.query.filter_by(parent_id=category_id, is_public=True).all()

    # Get pages in this category
    pages = Page.query.filter_by(category_id=category_id, is_published=True)\
                     .order_by(Page.title).all()

    # Filter pages based on permissions
    accessible_pages = [page for page in pages if page.can_view(current_user)]

    # Build category tree with pages for sidebar
    def build_category_tree_with_pages(categories, parent_id=None):
        tree = []
        for cat in categories:
            if cat.parent_id == parent_id:
                # Get pages in this category
                category_pages = Page.query.filter_by(category_id=cat.id, is_published=True)\
                                       .order_by(Page.title).all()
                accessible_category_pages = [page for page in category_pages if page.can_view(current_user)]

                # Get child categories
                children = build_category_tree_with_pages(categories, cat.id)

                tree.append({
                    'category': cat,
                    'pages': accessible_category_pages,
                    'children': children
                })
        return tree

    # Get data for sidebar
    all_categories = Category.query.all()
    category_tree = build_category_tree_with_pages(all_categories)

    recent_pages = Page.query.filter_by(is_published=True)\
                           .order_by(Page.updated_at.desc()).limit(10).all()
    accessible_recent_pages = [page for page in recent_pages if page.can_view(current_user)]

    return render_template('wiki/category_confluence.html', category=category,
                         child_categories=child_categories, pages=accessible_pages,
                         category_tree=category_tree, recent_pages=accessible_recent_pages)


@wiki.route('/page/<slug>')
def view_page(slug):
    """View a wiki page using Confluence-style layout"""
    page = Page.query.filter_by(slug=slug).first_or_404()

    # Check permissions
    if not page.can_view(current_user):
        if current_user.is_authenticated:
            abort(403)
        else:
            return redirect(url_for('auth.login', next=request.url))

    # Increment view count
    page.increment_view_count()
    db.session.commit()

    # Get page history
    versions = page.versions.order_by(PageVersion.version_number.desc()).limit(10).all()

    # Get attachments
    attachments = Attachment.query.filter_by(page_id=page.id).all()
    accessible_attachments = [att for att in attachments if att.can_view(current_user)]

    # Get all categories for the editor and sidebar
    categories = Category.query.all()

    # Build category tree with pages
    def build_category_tree_with_pages(categories, parent_id=None):
        tree = []
        for category in categories:
            if category.parent_id == parent_id:
                # Get pages in this category
                category_pages = Page.query.filter_by(category_id=category.id, is_published=True)\
                                       .order_by(Page.title).all()
                accessible_category_pages = [page for page in category_pages if page.can_view(current_user)]

                # Get child categories
                children = build_category_tree_with_pages(categories, category.id)

                tree.append({
                    'category': category,
                    'pages': accessible_category_pages,
                    'children': children
                })
        return tree

    category_tree = build_category_tree_with_pages(categories)

    # Get recent pages for sidebar
    recent_pages = Page.query.filter_by(is_published=True)\
                           .order_by(Page.updated_at.desc()).limit(10).all()
    accessible_recent_pages = [page for page in recent_pages if page.can_view(current_user)]

    return render_template('wiki/page_confluence.html', page=page, versions=versions,
                         attachments=accessible_attachments, categories=categories,
                         category_tree=category_tree, recent_pages=accessible_recent_pages,
                         target_type='page', target_id=page.id)

@wiki.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.WRITE)
def create_page():
    """Create a new page"""
    form = PageForm()
    form.category_id.choices = [(0, 'No Category')] + [(c.id, c.name) for c in Category.query.all()]

    if form.validate_on_submit():
        page = Page(
            title=form.title.data,
            content=form.content.data,
            summary=form.summary.data,
            author_id=current_user.id,
            category_id=form.category_id.data if form.category_id.data != 0 else None,
            is_published=form.is_published.data,
            is_public=form.is_public.data
        )

        db.session.add(page)
        db.session.commit()

        # Handle uploaded files - associate them with the page
        uploaded_files = request.form.get('uploaded_files')
        if uploaded_files:
            try:
                import json
                files_data = json.loads(uploaded_files)
                for file_data in files_data:
                    attachment = Attachment.query.get(file_data['id'])
                    if attachment and attachment.page_id is None:
                        attachment.page_id = page.id
                        print(f"Associated attachment {file_data['id']} with new page {page.id}")
            except Exception as e:
                print(f"Error processing uploaded files: {e}")

        # Ensure markdown rendering is triggered
        if page.content and not page.content_html:
            Page.on_changed_content(page, page.content, None, None)

        # Create initial version
        page.create_version(current_user.id, 'Initial version')
        db.session.commit()

        flash('Page created successfully!', 'success')
        return redirect(url_for('wiki.view_page', slug=page.slug))

    # Build category tree with pages for sidebar
    def build_category_tree_with_pages(categories, parent_id=None):
        tree = []
        for category in categories:
            if category.parent_id == parent_id:
                # Get pages in this category
                category_pages = Page.query.filter_by(category_id=category.id, is_published=True)\
                                       .order_by(Page.title).all()
                accessible_category_pages = [page for page in category_pages if page.can_view(current_user)]

                # Get child categories
                children = build_category_tree_with_pages(categories, category.id)

                tree.append({
                    'category': category,
                    'pages': accessible_category_pages,
                    'children': children
                })
        return tree

    # Get data for sidebar
    all_categories = Category.query.all()
    category_tree = build_category_tree_with_pages(all_categories)

    recent_pages = Page.query.filter_by(is_published=True)\
                           .order_by(Page.updated_at.desc()).limit(10).all()
    accessible_recent_pages = [page for page in recent_pages if page.can_view(current_user)]

    return render_template('wiki/create_page_confluence.html', form=form, is_edit=False,
                         category_tree=category_tree, recent_pages=accessible_recent_pages)

@wiki.route('/edit/<int:page_id>', methods=['GET', 'POST'])
@login_required
def edit_page(page_id):
    """Edit an existing page"""
    page = Page.query.get_or_404(page_id)

    # Check permissions
    if not page.can_edit(current_user):
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({'success': False, 'message': 'Permission denied'}), 403
        abort(403)

    # Handle AJAX requests for click-to-edit functionality
    if request.headers.get('Content-Type') == 'application/json' or request.is_json:
        return handle_edit_ajax(page)

    # Traditional form-based editing
    form = PageForm(obj=page)
    form.category_id.choices = [(0, 'No Category')] + [(c.id, c.name) for c in Category.query.all()]

    if form.validate_on_submit():
        # Create version before updating
        old_content = page.content
        old_title = page.title

        page.title = form.title.data
        page.content = form.content.data
        page.summary = form.summary.data
        page.category_id = form.category_id.data if form.category_id.data != 0 else None
        page.is_published = form.is_published.data
        page.is_public = form.is_public.data
        page.last_editor_id = current_user.id

        # Ensure markdown rendering is triggered
        if page.content and (not page.content_html or old_content != page.content):
            Page.on_changed_content(page, page.content, old_content, None)

        # Determine change summary
        change_summary = []
        if old_title != form.title.data:
            change_summary.append(f"Title changed: '{old_title}' → '{form.title.data}'")
        if form.change_summary.data:
            change_summary.append(form.change_summary.data)

        page.create_version(current_user.id, '; '.join(change_summary) if change_summary else 'Updated')
        db.session.commit()

        flash('Page updated successfully!', 'success')
        return redirect(url_for('wiki.view_page', slug=page.slug))

    # Build category tree with pages for sidebar
    def build_category_tree_with_pages(categories, parent_id=None):
        tree = []
        for category in categories:
            if category.parent_id == parent_id:
                # Get pages in this category
                category_pages = Page.query.filter_by(category_id=category.id, is_published=True)\
                                       .order_by(Page.title).all()
                accessible_category_pages = [page for page in category_pages if page.can_view(current_user)]

                # Get child categories
                children = build_category_tree_with_pages(categories, category.id)

                tree.append({
                    'category': category,
                    'pages': accessible_category_pages,
                    'children': children
                })
        return tree

    # Get data for sidebar
    all_categories = Category.query.all()
    category_tree = build_category_tree_with_pages(all_categories)

    recent_pages = Page.query.filter_by(is_published=True)\
                           .order_by(Page.updated_at.desc()).limit(10).all()
    accessible_recent_pages = [page for page in recent_pages if page.can_view(current_user)]

    return render_template('wiki/edit_page_confluence.html', form=form, page=page, is_edit=True,
                         category_tree=category_tree, recent_pages=accessible_recent_pages)

def handle_edit_ajax(page):
    """Handle AJAX edit requests from click-to-edit functionality"""
    try:
        # Get form data
        if request.is_json:
            data = request.get_json()
            title = data.get('title', '').strip()
            content = data.get('content', '')
            category_id = data.get('category_id', type=int)
            is_draft = data.get('save_draft') == 'true'
            uploaded_files = data.get('uploaded_files', [])
        else:
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '')
            category_id = request.form.get('category_id', type=int)
            is_draft = request.form.get('save_draft') == 'true'
            uploaded_files = []

        # Validate required fields
        if not title:
            return jsonify({'success': False, 'message': 'Title is required'}), 400

        # Create version before updating
        old_title = page.title
        old_content = page.content

        # Update page
        page.title = title
        page.content = content
        page.last_editor_id = current_user.id

        if category_id and category_id > 0:
            page.category_id = category_id

        # Generate summary from content if not provided
        if not page.summary and content:
            page.generate_summary()

        # Handle uploaded files - associate them with the page
        if uploaded_files:
            from app.models import Attachment
            for file_data in uploaded_files:
                attachment = Attachment.query.get(file_data['id'])
                if attachment and attachment.page_id is None:
                    attachment.page_id = page.id
                    print(f"Associated attachment {file_data['id']} with page {page.id}")

        # Determine change summary
        change_summary = []
        if old_title != title:
            change_summary.append(f"Title changed")
        if old_content != content:
            change_summary.append("Content updated")

        # Auto-generate slug if title changed
        if old_title != title:
            page.generate_slug()

        # Only create version for non-draft saves
        if not is_draft:
            page.create_version(current_user.id, '; '.join(change_summary) if change_summary else 'Updated')
            page.is_published = True  # Auto-publish when saving

        db.session.commit()

        response_data = {
            'success': True,
            'message': 'Draft saved' if is_draft else 'Page updated successfully',
            'page': {
                'id': page.id,
                'title': page.title,
                'slug': page.slug,
                'content_html': page.content_html,
                'updated_at': page.updated_at.isoformat()
            }
        }

        return jsonify(response_data)

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating page {page.id}: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred while saving the page'}), 500

@wiki.route('/delete/<int:page_id>', methods=['POST'])
@login_required
def delete_page(page_id):
    """Delete a page"""
    page = Page.query.get_or_404(page_id)

    # Check permissions
    if not current_user.is_administrator() and page.author_id != current_user.id:
        abort(403)

    db.session.delete(page)
    db.session.commit()
    flash('Page deleted successfully!', 'success')
    return redirect(url_for('wiki.index'))

@wiki.route('/history/<int:page_id>')
@login_required
def page_history(page_id):
    """View page version history"""
    page = Page.query.get_or_404(page_id)

    if not page.can_view(current_user):
        abort(403)

    versions = page.versions.order_by(PageVersion.version_number.desc()).all()
    # Build category tree with pages for sidebar
    def build_category_tree_with_pages(categories, parent_id=None):
        tree = []
        for category in categories:
            if category.parent_id == parent_id:
                # Get pages in this category
                category_pages = Page.query.filter_by(category_id=category.id, is_published=True)\
                                       .order_by(Page.title).all()
                accessible_category_pages = [page for page in category_pages if page.can_view(current_user)]
                children = build_category_tree_with_pages(categories, category.id)
                tree.append({
                    'category': category,
                    'pages': accessible_category_pages,
                    'children': children
                })
        return tree

    # Get data for sidebar
    all_categories = Category.query.all()
    category_tree = build_category_tree_with_pages(all_categories)

    recent_pages = Page.query.filter_by(is_published=True)\
                           .order_by(Page.updated_at.desc()).limit(10).all()
    accessible_recent_pages = [page for page in recent_pages if page.can_view(current_user)]

    return render_template('wiki/history_confluence.html', page=page, versions=versions,
                         category_tree=category_tree, recent_pages=accessible_recent_pages)

@wiki.route('/version/<int:version_id>')
@login_required
def view_version(version_id):
    """View a specific version of a page"""
    version = PageVersion.query.get_or_404(version_id)

    if not version.page.can_view(current_user):
        abort(403)

    # Create a temporary page object for display
    temp_page = Page()
    temp_page.title = version.title
    temp_page.content = version.content
    temp_page.content_html = version.content_html
    temp_page.created_at = version.created_at
    temp_page.author = version.author
    temp_page.last_editor = version.editor
    temp_page.slug = version.page.slug  # Add slug from the original page
    temp_page.id = version.page.id  # Add ID from the original page

    # Build category tree with pages for sidebar
    def build_category_tree_with_pages(categories, parent_id=None):
        tree = []
        for category in categories:
            if category.parent_id == parent_id:
                # Get pages in this category
                category_pages = Page.query.filter_by(category_id=category.id, is_published=True)\
                                       .order_by(Page.title).all()
                accessible_category_pages = [page for page in category_pages if page.can_view(current_user)]
                children = build_category_tree_with_pages(categories, category.id)
                tree.append({
                    'category': category,
                    'pages': accessible_category_pages,
                    'children': children
                })
        return tree

    # Get data for sidebar
    all_categories = Category.query.all()
    category_tree = build_category_tree_with_pages(all_categories)

    recent_pages = Page.query.filter_by(is_published=True)\
                           .order_by(Page.updated_at.desc()).limit(10).all()
    accessible_recent_pages = [page for page in recent_pages if page.can_view(current_user)]

    return render_template('wiki/version_confluence.html', page=temp_page, version=version,
                         category_tree=category_tree, recent_pages=accessible_recent_pages)

@wiki.route('/restore/<int:page_id>/<int:version_number>', methods=['POST'])
@login_required
def restore_version(page_id, version_number):
    """Restore a page to a specific version"""
    page = Page.query.get_or_404(page_id)

    if not page.can_edit(current_user):
        abort(403)

    if page.restore_version(version_number, current_user.id):
        db.session.commit()
        flash(f'Page restored to version {version_number}', 'success')
    else:
        flash('Failed to restore version', 'danger')

    return redirect(url_for('wiki.view_page', slug=page.slug))

@wiki.route('/preview', methods=['POST'])
def preview_markdown():
    """Preview markdown content"""
    # Check if it's form data or JSON
    if request.is_json:
        content = request.json.get('content', '')
    else:
        content = request.form.get('content', '')

    # Convert markdown to HTML
    html = markdown.markdown(content, extensions=['codehilite', 'tables', 'toc'])

    # Sanitize HTML
    allowed_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'strong', 'em',
                   'u', 'ol', 'ul', 'li', 'code', 'pre', 'blockquote', 'a',
                   'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td']
    allowed_attrs = {'a': ['href', 'title'], 'img': ['src', 'alt', 'title', 'width', 'height']}

    clean_html = bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs)

    return jsonify({'html': clean_html})

@wiki.route('/upload', methods=['POST'])
@login_required
@permission_required(Permission.WRITE)
def upload_file():
    """Upload a file attachment"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file selected'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file and allowed_file(file.filename):
        # 初始化存储服务
        storage_service = create_storage_service(current_app.config['STORAGE_CONFIG'])

        # 使用存储服务上传文件
        folder = request.form.get('folder', 'attachments')  # 默认文件夹
        upload_result = storage_service.upload_file(
            file_data=file,
            filename=file.filename,
            content_type=file.mimetype,
            folder=folder
        )

        if not upload_result['success']:
            return jsonify({'error': upload_result.get('message', 'Upload failed')}), 500

        # Create attachment record
        page_id = request.form.get('page_id', type=int)
        attachment = Attachment(
            filename=upload_result['filename'],
            original_filename=upload_result['original_filename'],
            file_path=upload_result['relative_path'],  # 存储相对路径而不是绝对路径
            file_size=upload_result['file_size'],
            mime_type=file.mimetype,
            page_id=page_id,
            uploaded_by=current_user.id,
            description=request.form.get('description', '')
        )

        db.session.add(attachment)
        db.session.commit()

        return jsonify({
            'success': True,
            'attachment': {
                'id': attachment.id,
                'filename': upload_result['filename'],
                'original_filename': upload_result['original_filename'],
                'url': upload_result['url'],  # 使用存储服务返回的URL
                'size': attachment.get_size_display()
            }
        })

    return jsonify({'error': 'File type not allowed'}), 400

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']