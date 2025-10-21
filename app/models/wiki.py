from datetime import datetime
from sqlalchemy import text
from app import db
import bleach
import re

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, index=True)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    sort_order = db.Column(db.Integer, default=0)
    is_public = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relationships
    parent = db.relationship('Category', remote_side=[id], backref='children')
    pages = db.relationship('Page', backref='category', lazy='dynamic')
    creator = db.relationship('User', foreign_keys=[created_by])

    def __repr__(self):
        return f'<Category {self.name}>'

    def get_path(self):
        if self.parent:
            return f'{self.parent.get_path()} / {self.name}'
        return self.name

    def get_ancestors(self):
        ancestors = []
        current = self
        while current.parent:
            ancestors.append(current.parent)
            current = current.parent
        return ancestors

    def would_create_cycle(self, parent_id):
        """Check if setting parent_id would create a circular relationship"""
        if parent_id is None or parent_id == 0:
            return False

        # Get the potential parent
        from app.models.user import User
        parent = Category.query.get(parent_id)
        if not parent:
            return False

        # Check if this category is already an ancestor of the potential parent
        current = parent
        visited = set()
        while current and current.id not in visited:
            if current.id == self.id:
                return True  # This would create a cycle
            visited.add(current.id)
            current = current.parent

        return False

class Page(db.Model):
    __tablename__ = 'pages'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), index=True)
    slug = db.Column(db.String(128), unique=True, index=True)
    content = db.Column(db.Text)
    content_html = db.Column(db.Text)
    summary = db.Column(db.String(500))
    is_published = db.Column(db.Boolean, default=False)
    is_public = db.Column(db.Boolean, default=True)
    allow_comments = db.Column(db.Boolean, default=True)
    view_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = db.Column(db.DateTime)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    last_editor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    template = db.Column(db.String(64), default='default')
  
    # Search indexes
    __table_args__ = (
        db.Index('ix_pages_search', 'title', 'summary'),
    )

    # Relationships
    author = db.relationship('User', foreign_keys=[author_id], backref='authored_pages')
    last_editor = db.relationship('User', foreign_keys=[last_editor_id], backref='edited_pages')
    versions = db.relationship('PageVersion', backref='page', lazy='dynamic', cascade='all, delete-orphan')
    attachments = db.relationship('Attachment', backref='page', lazy='dynamic', cascade='all, delete-orphan')
    
    # Permission fields
    read_permission = db.Column(db.String(64), default='all')  # all, logged_in, specific_roles
    write_permission = db.Column(db.String(64), default='author')  # author, specific_roles
    allowed_read_roles = db.Column(db.Text)  # JSON array of role names
    allowed_write_roles = db.Column(db.Text)  # JSON array of role names

    def __init__(self, **kwargs):
        super(Page, self).__init__(**kwargs)
        if self.slug is None and self.title:
            self.generate_slug()
        if self.summary is None and self.content:
            self.generate_summary()

    def __repr__(self):
        return f'<Page {self.title}>'

    @staticmethod
    def on_changed_content(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br',
                        'div', 'span', 'table', 'thead', 'tbody', 'tr', 'th', 'td']
        allowed_attrs = {'a': ['href', 'title'], 'abbr': ['title'], 'acronym': ['title']}
        html = bleach.linkify(bleach.clean(value, tags=allowed_tags, attributes=allowed_attrs, strip=True))
        target.content_html = html

    def generate_slug(self):
        import re
        from unidecode import unidecode

        # Generate base slug from title
        base_slug = re.sub(r'[^\w]+', '-', unidecode(self.title)).strip('-')
        base_slug = base_slug.lower()

        # If base_slug is empty, use a default
        if not base_slug:
            base_slug = 'untitled'

        # Check if slug already exists and add number suffix if needed
        slug = base_slug
        counter = 1
        while True:
            # Check if slug exists (exclude current page if it has an id)
            existing_page = Page.query.filter_by(slug=slug).first()
            if existing_page is None or (self.id and existing_page.id == self.id):
                self.slug = slug
                break

            # Try next slug with number
            slug = f"{base_slug}-{counter}"
            counter += 1

    def generate_summary(self):
        if self.content:
            import markdown
            # Remove markdown syntax for summary
            text = self.content
            text = re.sub(r'[#*`\[\]()]', '', text)
            text = re.sub(r'\n+', ' ', text)
            self.summary = text[:477] + '...' if len(text) > 477 else text

    def can_view(self, user):
        if self.is_public:
            return True
        if user is None or not hasattr(user, 'id') or not hasattr(user, 'is_administrator'):
            return False
        if user.is_administrator():
            return True
        if user.id == self.author_id:
            return True
        if self.read_permission == 'logged_in':
            return True
        if self.read_permission == 'specific_roles' and self.allowed_read_roles:
            import json
            allowed_roles = json.loads(self.allowed_read_roles)
            return user.role.name in allowed_roles
        return False

    def can_edit(self, user):
        if user is None or not hasattr(user, 'id') or not hasattr(user, 'is_administrator'):
            return False
        if user.is_administrator():
            return True
        if user.id == self.author_id:
            return True
        if self.write_permission == 'all':
            return True
        if self.write_permission == 'specific_roles' and self.allowed_write_roles:
            import json
            allowed_roles = json.loads(self.allowed_write_roles)
            return user.role.name in allowed_roles
        return False

    def increment_view_count(self):
        self.view_count += 1
        db.session.add(self)

    def create_version(self, editor_id=None, change_summary=''):
        if not editor_id:
            editor_id = self.author_id

        version = PageVersion(
            page_id=self.id,
            title=self.title,
            content=self.content,
            content_html=self.content_html,
            author_id=self.author_id,
            editor_id=editor_id,
            change_summary=change_summary,
            version_number=self.versions.count() + 1
        )
        db.session.add(version)
        return version

    def get_latest_version(self):
        return self.versions.order_by(PageVersion.version_number.desc()).first()

    def restore_version(self, version_number, editor_id):
        version = self.versions.filter_by(version_number=version_number).first()
        if version:
            self.title = version.title
            self.content = version.content
            self.content_html = version.content_html
            self.last_editor_id = editor_id
            self.create_version(editor_id, f'Restored to version {version_number}')
            db.session.add(self)
            return True
        return False

  
    def to_dict(self, include_content=False):
        data = {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'summary': self.summary,
            'is_published': self.is_published,
            'is_public': self.is_public,
            'view_count': self.view_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'author': self.author.username if self.author else None,
            'category': self.category.name if self.category else None,
            'template': self.template,
          }
        if include_content:
            data['content'] = self.content
            data['content_html'] = self.content_html
        return data

class PageVersion(db.Model):
    __tablename__ = 'page_versions'
    id = db.Column(db.Integer, primary_key=True)
    page_id = db.Column(db.Integer, db.ForeignKey('pages.id'))
    title = db.Column(db.String(128))
    content = db.Column(db.Text)
    content_html = db.Column(db.Text)
    version_number = db.Column(db.Integer)
    change_summary = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    editor_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relationships
    author = db.relationship('User', foreign_keys=[author_id])
    editor = db.relationship('User', foreign_keys=[editor_id])

    def __repr__(self):
        return f'<PageVersion {self.page_id}-{self.version_number}>'

    def to_dict(self):
        return {
            'id': self.id,
            'page_id': self.page_id,
            'title': self.title,
            'content': self.content,
            'version_number': self.version_number,
            'change_summary': self.change_summary,
            'created_at': self.created_at.isoformat(),
            'author': self.author.username if self.author else None,
            'editor': self.editor.username if self.editor else None
        }

class Attachment(db.Model):
    __tablename__ = 'attachments'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255))
    original_filename = db.Column(db.String(255))
    file_path = db.Column(db.String(500))
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    page_id = db.Column(db.Integer, db.ForeignKey('pages.id'))
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text)
    is_public = db.Column(db.Boolean, default=True)

    # Relationships
    uploader = db.relationship('User')

    def __init__(self, **kwargs):
        super(Attachment, self).__init__(**kwargs)

    def __repr__(self):
        return f'<Attachment {self.filename}>'

    def get_file_extension(self):
        return self.filename.split('.')[-1].lower() if '.' in self.filename else ''

    def is_image(self):
        return self.mime_type and self.mime_type.startswith('image/')

    def get_size_display(self):
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"

    def can_view(self, user):
        if self.is_public:
            return True
        if user is None or not hasattr(user, 'id') or not hasattr(user, 'is_administrator'):
            return False
        if user.is_administrator():
            return True
        if user.id == self.uploaded_by:
            return True
        if self.page and self.page.can_view(user):
            return True
        return False

# Register event listeners
from sqlalchemy import event

@event.listens_for(Page.content, 'set')
def on_page_content_change(target, value, oldvalue, initiator):
    Page.on_changed_content(target, value, oldvalue, initiator)
    target.updated_at = datetime.utcnow()
    if target.summary is None or not target.summary:
        target.generate_summary()