from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.models import Page, Category, Attachment, PageVersion, Permission
from app.decorators import permission_required
from app.forms.wiki import PageForm, CategoryForm, SearchForm
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

    return render_template('wiki/index_confluence_static.html', categories=categories, recent_pages=accessible_pages)

@wiki.route('/search')
def search():
    """Search pages"""
    form = SearchForm()
    page = request.args.get('page', 1, type=int)
    query = request.args.get('q', '').strip()

    if not query:
        return render_template('wiki/search.html', form=form, results=None, query='')

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

    return render_template('wiki/search.html', form=form, pages=accessible_pages,
                         query=query, pagination=pages)

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

    return render_template('wiki/category.html', category=category,
                         child_categories=child_categories, pages=accessible_pages)


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

    return render_template('wiki/page_confluence.html', page=page, versions=versions,
                         attachments=accessible_attachments, categories=categories)

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
            parent_id=form.parent_id.data if form.parent_id.data != 0 else None,
            sort_order=form.sort_order.data if form.sort_order.data is not None else 0,
            is_published=form.is_published.data,
            is_public=form.is_public.data
        )

        db.session.add(page)
        db.session.commit()

        # Create initial version
        page.create_version(current_user.id, 'Initial version')
        db.session.commit()

        flash('Page created successfully!', 'success')
        return redirect(url_for('wiki.view_page', slug=page.slug))

    return render_template('wiki/edit_page.html', form=form, is_edit=False)

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
        page.parent_id = form.parent_id.data if form.parent_id.data != 0 else None
        page.sort_order = form.sort_order.data if form.sort_order.data is not None else 0
        page.is_published = form.is_published.data
        page.is_public = form.is_public.data
        page.last_editor_id = current_user.id

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

    return render_template('wiki/edit_page.html', form=form, page=page, is_edit=True)

def handle_edit_ajax(page):
    """Handle AJAX edit requests from click-to-edit functionality"""
    try:
        # Get form data
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '')
        category_id = request.form.get('category_id', type=int)
        is_draft = request.form.get('save_draft') == 'true'

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
    return render_template('wiki/history.html', page=page, versions=versions)

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

    return render_template('wiki/version.html', page=temp_page, version=version)

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
        filename = secure_filename(file.filename)
        # Add timestamp to make filename unique
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"

        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        file.save(upload_path)

        # Create attachment record
        page_id = request.form.get('page_id', type=int)
        attachment = Attachment(
            filename=unique_filename,
            original_filename=filename,
            file_path=upload_path,
            file_size=os.path.getsize(upload_path),
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
                'filename': unique_filename,
                'original_filename': filename,
                'url': url_for('static', filename=f'uploads/{unique_filename}'),
                'size': attachment.get_size_display()
            }
        })

    return jsonify({'error': 'File type not allowed'}), 400

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']