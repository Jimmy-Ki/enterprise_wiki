# Enterprise Wiki

A comprehensive enterprise knowledge base and wiki system built with Flask and SQLite, featuring role-based permissions, markdown editing, version control, and robust security features.

## Features

### Core Functionality
- **Full-featured Wiki System**: Create, edit, and organize knowledge base pages
- **Markdown Editor**: Real-time preview with syntax highlighting
- **Version Control**: Track page changes with version history
- **File Attachments**: Upload and manage documents, images, and files
- **Full-text Search**: Powerful search across all content
- **Category Organization**: Hierarchical category structure

### Security & Permissions
- **Role-based Access Control**: Multiple permission levels (Viewer, Editor, Moderator, Administrator)
- **User Authentication**: Secure login with session management
- **Account Security**: Account lockout after failed attempts, session management
- **CSRF Protection**: Cross-site request forgery prevention
- **XSS Protection**: Input sanitization and HTML escaping
- **Rate Limiting**: Prevent abuse with configurable rate limits

### Admin Features
- **User Management**: Create, edit, and manage user accounts
- **Role Management**: Configure permissions and access levels
- **Content Moderation**: Review and manage all wiki content
- **System Monitoring**: Dashboard with statistics and health checks
- **Backup System**: Automated database backups

### API & Integration
- **RESTful API**: Complete API for external integrations
- **Webhook Support**: Event-driven notifications
- **Export Functionality**: Export content in various formats

## Quick Start

### Prerequisites
- Python 3.8+
- SQLite 3
- Redis (optional, for rate limiting and caching)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourcompany/enterprise-wiki.git
cd enterprise-wiki
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Initialize database**
```bash
flask deploy
```

6. **Run the application**
```bash
python run.py
```

7. **Access the application**
- Open http://localhost:5000 in your browser
- Default admin: admin@company.com / admin123 (change immediately!)

## Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Security
SECRET_KEY=your-secret-key-here
ADMIN_EMAIL=admin@yourcompany.com

# Database
DATABASE_URL=sqlite:///enterprise_wiki.db

# Email (for password resets, confirmations)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Redis (optional)
REDIS_URL=redis://localhost:6379/0
```

### Permission Levels

- **Viewer**: Read public and authenticated content
- **Editor**: Create and edit own content
- **Moderator**: Edit all content, moderate discussions
- **Administrator**: Full system access

## Usage

### Creating Content

1. **Create a Page**
   - Click "Create Page" in the navigation
   - Enter title and content using Markdown
   - Set category and visibility options
   - Save to publish

2. **Using the Markdown Editor**
   - Real-time preview as you type
   - Toolbar for common formatting
   - Keyboard shortcuts (Ctrl+B for bold, Ctrl+I for italic)
   - Auto-save functionality

3. **File Uploads**
   - Attach files to pages
   - Supported formats: PDF, images, Office documents
   - File size limit: 16MB (configurable)

### Managing Users

1. **User Registration**
   - Users can self-register (if enabled)
   - Email confirmation required
   - Default role: Viewer

2. **Admin Management**
   - Access Admin panel
   - Manage user accounts and roles
   - Monitor system activity

### API Usage

The system provides a RESTful API for external integrations:

```bash
# Get all pages
GET /api/pages

# Get specific page
GET /api/pages/123

# Create page (authentication required)
POST /api/pages
Content-Type: application/json
{
  "title": "New Page",
  "content": "# Markdown content",
  "is_published": true
}

# Search pages
GET /api/search?q=query
```

## Security Considerations

### Production Deployment

1. **Change Default Credentials**
   - Update admin password immediately
   - Generate a strong `SECRET_KEY`

2. **Enable HTTPS**
   - Set `FORCE_HTTPS=true` in production
   - Configure SSL certificates

3. **Database Security**
   - Set appropriate file permissions
   - Enable regular backups

4. **Rate Limiting**
   - Configure Redis for rate limiting
   - Set appropriate limits for API endpoints

### Monitoring

- System health checks: `/api/health`
- Admin dashboard with statistics
- Security event logging
- Performance monitoring

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

```bash
# Format code
black .

# Sort imports
isort .

# Lint code
flake8 .
```

### Database Migrations

```bash
# Create migration
flask db migrate -m "Description"

# Apply migration
flask db upgrade
```

## Deployment

### Production Server

1. **Using Gunicorn**
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

2. **Using Supervisor**
```ini
[program:enterprise-wiki]
command=/path/to/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 run:app
directory=/path/to/enterprise-wiki
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
```

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app"]
```

## Troubleshooting

### Common Issues

1. **Database Lock Errors**
   - Ensure SQLite file permissions are correct
   - Check for long-running transactions

2. **Email Not Sending**
   - Verify SMTP configuration
   - Check email credentials and security settings

3. **Redis Connection Errors**
   - Ensure Redis is running
   - Check connection URL and firewall settings

4. **Permission Denied Errors**
   - Check user roles and permissions
   - Verify page access settings

### Logs

- Application logs: `logs/enterprise_wiki.log`
- Security events: Redis key `security_events`
- User activities: Redis key `user_activities`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the GitHub repository
- Contact the development team
- Check the documentation at `/docs` within the application

## Changelog

### Version 1.0.0
- Initial release
- Core wiki functionality
- User authentication and authorization
- Markdown editor with preview
- Version control system
- File upload support
- Search functionality
- Admin dashboard
- RESTful API
- Security features
- Documentation