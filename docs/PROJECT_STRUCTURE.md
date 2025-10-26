# Enterprise Wiki - Complete Project Structure

## 📁 Directory Structure

```
enterprise_wiki/
├── app/                          # Main application package
│   ├── __init__.py              # Flask app factory and configuration
│   ├── models/                  # Database models
│   │   ├── __init__.py         # Model imports
│   │   ├── user.py             # User, Role, Permission models
│   │   ├── wiki.py             # Page, Category, Attachment models
│   │   └── search.py           # Search index models
│   ├── views/                   # Route controllers (Blueprints)
│   │   ├── __init__.py         # Views package
│   │   ├── auth.py             # Authentication routes
│   │   ├── wiki.py             # Wiki page routes
│   │   ├── admin.py            # Admin dashboard routes
│   │   └── api.py              # REST API routes
│   ├── forms/                   # WTForms classes
│   │   ├── __init__.py         # Forms package
│   │   ├── auth.py             # Authentication forms
│   │   └── wiki.py             # Wiki and admin forms
│   ├── templates/               # Jinja2 templates
│   │   ├── base.html           # Base template with navigation
│   │   ├── auth/               # Authentication templates
│   │   │   ├── login.html      # Login page
│   │   │   ├── register.html   # Registration page
│   │   │   ├── unconfirmed.html # Email confirmation page
│   │   │   ├── change_password.html # Password change page
│   │   │   └── email/          # Email templates
│   │   │       ├── confirm.txt
│   │   │       ├── confirm.html
│   │   │       ├── reset_password.txt
│   │   │       └── reset_password.html
│   │   ├── wiki/               # Wiki page templates
│   │   │   ├── index.html      # Wiki home page
│   │   │   ├── page.html       # Page view template
│   │   │   ├── edit_page.html  # Page editor template
│   │   │   ├── search.html     # Search results page
│   │   │   └── category.html   # Category view template
│   │   ├── admin/              # Admin dashboard templates
│   │   │   └── dashboard.html  # Admin dashboard
│   │   │   └── users.html      # User management
│   │   └── errors/             # Error page templates
│   │       ├── 403.html        # Access denied
│   │       ├── 404.html        # Page not found
│   │       └── 500.html        # Server error
│   ├── static/                  # Static files
│   │   ├── css/
│   │   │   └── markdown-editor.css # Editor styles
│   │   ├── js/
│   │   │   └── markdown-editor.js  # Rich text editor
│   │   ├── images/              # Image assets
│   │   └── uploads/             # User uploaded files
│   ├── security.py              # Security utilities and middleware
│   ├── utils.py                 # Helper functions and utilities
│   ├── email.py                 # Email sending utilities
│   └── decorators.py            # Custom decorators
├── config/                      # Configuration files
│   └── config.py               # Flask configuration classes
├── migrations/                  # Database migration files
├── tests/                       # Test files
├── docs/                        # Documentation
├── logs/                        # Application logs
├── backups/                     # Database backups
├── search_index/               # Whoosh search index files
├── requirements.txt            # Python dependencies
├── setup.py                    # Package setup file
├── run.py                      # Application entry point
├── install.sh                  # Installation script
├── Dockerfile                  # Docker configuration
├── docker-compose.yml          # Docker Compose setup
├── Procfile                    # Heroku deployment file
├── .env.example               # Environment variables template
├── .gitignore                  # Git ignore file
└── README.md                   # Project documentation
```

## 🚀 Key Features Implemented

### 1. **Authentication & Authorization**
- ✅ User registration with email confirmation
- ✅ Secure login/logout with session management
- ✅ Password reset functionality
- ✅ Role-based access control (Viewer, Editor, Moderator, Admin)
- ✅ Account lockout protection
- ✅ Session management and monitoring

### 2. **Wiki System**
- ✅ Markdown editor with real-time preview
- ✅ Page creation, editing, and deletion
- ✅ Version control and change history
- ✅ Hierarchical category organization
- ✅ Full-text search functionality
- ✅ File attachments and media upload
- ✅ Page permissions and visibility controls

### 3. **Admin Dashboard**
- ✅ User management interface
- ✅ Role and permission configuration
- ✅ Content moderation tools
- ✅ System statistics and monitoring
- ✅ Session management
- ✅ System health checks

### 4. **Security Features**
- ✅ CSRF protection on all forms
- ✅ XSS prevention with input sanitization
- ✅ SQL injection prevention with SQLAlchemy
- ✅ Rate limiting with Redis
- ✅ Secure password hashing
- ✅ Security event logging
- ✅ File upload validation

### 5. **API & Integration**
- ✅ RESTful API endpoints
- ✅ Authentication for API requests
- ✅ CRUD operations via API
- ✅ Search API
- ✅ File upload API
- ✅ Health check endpoints

### 6. **User Experience**
- ✅ Responsive Bootstrap design
- ✅ Mobile-friendly interface
- ✅ Real-time markdown preview
- ✅ Auto-save functionality
- ✅ Keyboard shortcuts
- ✅ Interactive notifications
- ✅ Error handling pages

### 7. **Deployment & DevOps**
- ✅ Docker containerization
- ✅ Installation script
- ✅ Environment configuration
- ✅ Database migrations
- ✅ Logging and monitoring
- ✅ Backup system
- ✅ Production deployment guide

## 🛠️ Technology Stack

### Backend
- **Flask** - Web framework
- **SQLAlchemy** - ORM and database management
- **SQLite** - Database (production-ready with proper configuration)
- **Flask-Login** - User session management
- **Flask-WTF** - Form handling and CSRF protection
- **Flask-Mail** - Email sending
- **Bleach** - HTML sanitization
- **Whoosh** - Full-text search
- **Redis** - Rate limiting and caching (optional)

### Frontend
- **Bootstrap 5** - UI framework
- **jQuery** - JavaScript utilities
- **Font Awesome** - Icons
- **Markdown.js** - Markdown processing
- **Chart.js** - Dashboard charts
- **Custom JavaScript** - Interactive features

### Security
- **Werkzeug** - Security utilities
- **bcrypt** - Password hashing
- **cryptography** - Encryption and security
- **CSRF tokens** - Request validation
- **Rate limiting** - Abuse prevention

### Development & Deployment
- **Docker** - Containerization
- **Gunicorn** - WSGI server
- **pytest** - Testing framework
- **Black** - Code formatting
- **Flake8** - Linting

## 📊 Database Schema

### Users & Authentication
- **users** - User accounts with roles and permissions
- **roles** - Permission groups (Viewer, Editor, Moderator, Admin)
- **user_sessions** - Active login sessions

### Content Management
- **pages** - Wiki pages with metadata
- **categories** - Hierarchical content organization
- **page_versions** - Version history for pages
- **attachments** - File attachments for pages

### Search & Indexing
- **search_index** - Whoosh search index data

## 🔐 Security Architecture

### Authentication Flow
1. User registration → Email confirmation → Account activation
2. Login with CSRF protection → Session creation → Last seen update
3. Failed login tracking → Account lockout after 5 attempts
4. Session management → Multi-device support → Session revocation

### Permission System
- **Viewer**: Read public/authenticated content
- **Editor**: Create and edit own content
- **Moderator**: Edit all content, moderate discussions
- **Administrator**: Full system access

### Security Measures
- CSRF tokens on all forms
- XSS protection with input sanitization
- SQL injection prevention with parameterized queries
- Rate limiting on sensitive endpoints
- File upload validation and sanitization
- Security event logging and monitoring

## 🚀 Deployment Options

### Development
```bash
./install.sh
source venv/bin/activate
python run.py
```

### Production (Docker)
```bash
docker-compose up -d
```

### Production (Manual)
```bash
pip install -r requirements.txt
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

## 📈 Performance Features

- **Database indexing** on frequently queried columns
- **Search optimization** with Whoosh full-text search
- **Caching** with Redis for rate limiting
- **Lazy loading** for large datasets
- **Pagination** for all list views
- **Image optimization** and file size limits
- **Compressed assets** and minified CSS/JS

## 🧪 Testing Coverage

- User authentication flows
- Wiki page CRUD operations
- Permission enforcement
- File upload security
- API endpoint functionality
- Error handling
- Form validation

## 📚 Documentation

- **README.md** - Installation and usage guide
- **API documentation** - REST API endpoints
- **Security guide** - Security best practices
- **Admin guide** - System administration
- **User guide** - End-user documentation

## 🔄 Future Enhancements

- Two-factor authentication
- LDAP/SSO integration
- Advanced analytics and reporting
- Content approval workflows
- Advanced search with filters
- Multi-language support
- Theme customization
- Plugin system
- API rate limiting per user
- Advanced backup strategies
- Performance monitoring dashboard

This Enterprise Wiki system is production-ready with comprehensive security, modern UI, and extensive functionality suitable for corporate knowledge management.