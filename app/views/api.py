from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from app.models import User, Page, Category, Attachment, Permission
from app.decorators import permission_required
import markdown

api = Blueprint('api', __name__)

def api_error(message, status_code=400):
    """Return JSON error response"""
    response = jsonify({'error': message})
    response.status_code = status_code
    return response

# API before_request removed to avoid header modification issue

@api.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

@api.route('/stats')
def api_stats():
    """Get system statistics (public)"""
    return jsonify({
        'total_pages': Page.query.filter_by(is_published=True).count(),
        'total_categories': Category.query.count(),
        'total_users': User.query.filter_by(is_active=True).count(),
        'total_attachments': Attachment.query.filter_by(is_public=True).count()
    })

@api.route('/pages')
def api_pages():
    """Get pages with optional filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    category_id = request.args.get('category_id', type=int)
    search = request.args.get('search', '', type=str)

    query = Page.query.filter_by(is_published=True)

    if category_id:
        query = query.filter_by(category_id=category_id)

    if search:
        query = query.filter(
            db.or_(
                Page.title.contains(search),
                Page.content.contains(search),
                Page.summary.contains(search)
            )
        )

    pages = query.paginate(page=page, per_page=per_page, error_out=False)

    # Filter pages based on permissions
    accessible_pages = []
    for page in pages.items:
        if page.can_view(None):  # Anonymous user
            accessible_pages.append(page.to_dict())

    return jsonify({
        'pages': accessible_pages,
        'pagination': {
            'page': pages.page,
            'pages': pages.pages,
            'per_page': pages.per_page,
            'total': pages.total,
            'has_next': pages.has_next,
            'has_prev': pages.has_prev
        }
    })

@api.route('/pages/<int:page_id>')
def api_page(page_id):
    """Get specific page"""
    page = Page.query.get_or_404(page_id)

    if not page.can_view(current_user):
        return api_error('Page not found', 404)

    return jsonify(page.to_dict(include_content=True))

@api.route('/pages/<int:page_id>', methods=['PUT'])
@login_required
@permission_required(Permission.WRITE)
def api_update_page(page_id):
    """Update page via API"""
    page = Page.query.get_or_404(page_id)

    if not page.can_edit(current_user):
        return api_error('Insufficient permissions', 403)

    data = request.get_json()
    if not data:
        return api_error('No data provided')

    # Update fields
    if 'title' in data:
        page.title = data['title']
    if 'content' in data:
        page.content = data['content']
    if 'summary' in data:
        page.summary = data['summary']
    if 'category_id' in data:
        page.category_id = data['category_id']
    if 'is_published' in data:
        page.is_published = data['is_published']
    if 'is_public' in data:
        page.is_public = data['is_public']

    page.last_editor_id = current_user.id
    page.create_version(current_user.id, 'API update')

    db.session.commit()

    return jsonify(page.to_dict(include_content=True))

@api.route('/pages', methods=['POST'])
@login_required
@permission_required(Permission.WRITE)
def api_create_page():
    """Create new page via API"""
    data = request.get_json()
    if not data:
        return api_error('No data provided')

    # Required fields
    if 'title' not in data or not data['title'].strip():
        return api_error('Title is required')

    if 'content' not in data or not data['content'].strip():
        return api_error('Content is required')

    page = Page(
        title=data['title'],
        content=data['content'],
        summary=data.get('summary', ''),
        author_id=current_user.id,
        category_id=data.get('category_id'),
        is_published=data.get('is_published', False),
        is_public=data.get('is_public', True)
    )

    db.session.add(page)
    db.session.commit()

    # Create initial version
    page.create_version(current_user.id, 'Created via API')
    db.session.commit()

    return jsonify(page.to_dict(include_content=True)), 201

@api.route('/pages/<int:page_id>', methods=['DELETE'])
@login_required
def api_delete_page(page_id):
    """Delete page via API"""
    page = Page.query.get_or_404(page_id)

    if not current_user.is_administrator() and page.author_id != current_user.id:
        return api_error('Insufficient permissions', 403)

    db.session.delete(page)
    db.session.commit()

    return jsonify({'message': 'Page deleted successfully'})

@api.route('/categories')
def api_categories():
    """Get categories with hierarchical structure"""
    try:
        categories = Category.query.all()

        def build_category_tree(cats, parent_id=None):
            tree = []
            for cat in cats:
                if cat.parent_id == parent_id:
                    children = build_category_tree(cats, cat.id)
                    tree.append({
                        'id': cat.id,
                        'name': cat.name,
                        'description': cat.description or '',
                        'parent_id': cat.parent_id,
                        'path': cat.get_path() if hasattr(cat, 'get_path') else '',
                        'children': children
                    })
            return tree

        return jsonify({
            'categories': build_category_tree(categories)
        })
    except Exception as e:
        return api_error(f'Error loading categories: {str(e)}', 500)

@api.route('/recent-pages')
def api_recent_pages():
    """Get recent pages"""
    try:
        days = request.args.get('days', 7, type=int)
        limit = request.args.get('limit', 10, type=int)

        since_date = datetime.utcnow() - timedelta(days=days)

        query = Page.query.filter(
            Page.updated_at >= since_date,
            Page.is_published == True
        ).order_by(Page.updated_at.desc())

        # Filter by permissions
        pages = []
        for page in query.limit(limit).all():
            # Handle both authenticated and anonymous users
            if page.can_view(current_user):
                pages.append({
                    'id': page.id,
                    'title': page.title,
                    'slug': page.slug,
                    'updated_at': page.updated_at.strftime('%Y-%m-%d %H:%M'),
                    'author': page.author.username if page.author else 'Unknown'
                })

        return jsonify({
            'pages': pages
        })
    except Exception as e:
        return api_error(f'Error loading recent pages: {str(e)}', 500)

@api.route('/pages/<int:page_id>', methods=['PATCH'])
@login_required
def api_patch_page(page_id):
    """Patch page via API for inline editing"""
    page = Page.query.get_or_404(page_id)

    if not page.can_edit(current_user):
        return api_error('Insufficient permissions', 403)

    data = request.get_json()
    if not data:
        return api_error('No data provided')

    # Update specific fields
    if 'title' in data:
        page.title = data['title'].strip()
        if not page.title:
            return api_error('Title cannot be empty')

    if 'content' in data:
        page.content = data['content']

    if 'summary' in data:
        page.summary = data['summary']

    if 'change_summary' in data:
        change_summary = data['change_summary']
    else:
        change_summary = 'Updated via inline editing'

    # Handle draft saving
    save_draft = data.get('save_draft', False)
    if not save_draft:
        page.is_published = True

    page.last_editor_id = current_user.id

    # Create version
    page.create_version(current_user.id, change_summary)

    # Render content
    import markdown
    import bleach
    if page.content:
        html = markdown.markdown(page.content, extensions=['codehilite', 'tables', 'toc'])
        allowed_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'strong', 'em',
                       'u', 'ol', 'ul', 'li', 'code', 'pre', 'blockquote', 'a',
                       'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td']
        allowed_attrs = {'a': ['href', 'title'], 'img': ['src', 'alt', 'title', 'width', 'height']}
        page.content_html = bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs)

    db.session.commit()

    return jsonify({
        'success': True,
        'page': page.to_dict(include_content=True),
        'rendered_content': page.content_html
    })

@api.route('/search')
def api_search():
    """Search pages via API"""
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 50)

    if not query:
        return api_error('Search query is required')

    # Use database search
    pages = Page.query.filter(
        Page.is_published == True,
        Page.is_public == True,
        db.or_(
            Page.title.contains(query),
            Page.content.contains(query),
            Page.summary.contains(query)
        )
    ).paginate(page=page, per_page=per_page, error_out=False)

    results = []
    for page in pages.items:
        if page.can_view(None):
            results.append({
                'id': page.id,
                'title': page.title,
                'summary': page.summary,
                'url': f'/wiki/{page.slug}',
                'updated_at': page.updated_at.isoformat(),
                'author': page.author.username if page.author else None
            })

    return jsonify({
        'results': results,
        'pagination': {
            'page': pages.page,
            'pages': pages.pages,
            'per_page': pages.per_page,
            'total': pages.total,
            'has_next': pages.has_next,
            'has_prev': pages.has_prev
        },
        'query': query
    })

@api.route('/preview', methods=['POST'])
@login_required
@permission_required(Permission.WRITE)
def api_preview():
    """Preview markdown content"""
    data = request.get_json()
    if not data or 'content' not in data:
        return api_error('Content is required')

    content = data['content']

    # Convert markdown to HTML
    html = markdown.markdown(content, extensions=['codehilite', 'tables', 'toc'])

    # Sanitize HTML
    import bleach
    allowed_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'strong', 'em',
                   'u', 'ol', 'ul', 'li', 'code', 'pre', 'blockquote', 'a',
                   'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td']
    allowed_attrs = {'a': ['href', 'title'], 'img': ['src', 'alt', 'title', 'width', 'height']}

    clean_html = bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs)

    return jsonify({'html': clean_html})

@api.route('/upload', methods=['POST'])
@login_required
@permission_required(Permission.WRITE)
def api_upload():
    """Upload file via API"""
    if 'file' not in request.files:
        return api_error('No file provided', 400)

    file = request.files['file']
    if file.filename == '':
        return api_error('No file selected', 400)

    from werkzeug.utils import secure_filename
    import os

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
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
            'id': attachment.id,
            'filename': unique_filename,
            'original_filename': filename,
            'url': url_for('static', filename=f'uploads/{unique_filename}'),
            'size': attachment.get_size_display(),
            'mime_type': attachment.mime_type
        }), 201

    return api_error('File type not allowed', 400)

def allowed_file(filename):
    """Check if file extension is allowed"""
    from flask import current_app
    ALLOWED_EXTENSIONS = current_app.config.get('ALLOWED_EXTENSIONS',
        {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'})
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@api.route('/users/me')
@login_required
def api_current_user():
    """Get current user info"""
    return jsonify(current_user.to_dict())

@api.route('/users/<int:user_id>/pages')
@login_required
def api_user_pages(user_id):
    """Get pages created by specific user"""
    user = User.query.get_or_404(user_id)

    # Only allow users to see their own pages or if admin
    if user_id != current_user.id and not current_user.is_administrator():
        return api_error('Insufficient permissions', 403)

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    pages = Page.query.filter_by(author_id=user_id)\
                     .order_by(Page.updated_at.desc())\
                     .paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'pages': [page.to_dict() for page in pages.items],
        'pagination': {
            'page': pages.page,
            'pages': pages.pages,
            'per_page': pages.per_page,
            'total': pages.total,
            'has_next': pages.has_next,
            'has_prev': pages.has_prev
        },
        'user': user.to_dict()
    })

@api.errorhandler(404)
def api_not_found(error):
    """API 404 handler"""
    if request.path.startswith('/api/'):
        return api_error('Resource not found', 404)
    return error

@api.errorhandler(403)
def api_forbidden(error):
    """API 403 handler"""
    if request.path.startswith('/api/'):
        return api_error('Access forbidden', 403)
    return error

@api.errorhandler(500)
def api_internal_error(error):
    """API 500 handler"""
    db.session.rollback()
    if request.path.startswith('/api/'):
        return api_error('Internal server error', 500)
    return error