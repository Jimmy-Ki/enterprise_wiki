import os
from app import create_app, db
from app.models import User, Role, Permission, Page, Category, Attachment, PageVersion, UserSession
from flask_migrate import upgrade

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role, Permission=Permission,
                Page=Page, Category=Category, Attachment=Attachment,
                PageVersion=PageVersion, UserSession=UserSession)

@app.cli.command()
def deploy():
    """Run deployment tasks."""
    upgrade()

    # Create default roles
    Role.insert_roles()

    # Create admin user if not exists
    admin_email = os.getenv('ADMIN_EMAIL', 'admin@company.com')
    if not User.query.filter_by(email=admin_email).first():
        admin = User(
            email=admin_email,
            username='admin',
            password='admin123',  # Change this immediately
            confirmed=True,
            role=Role.query.filter_by(name='Administrator').first()
        )
        db.session.add(admin)
        db.session.commit()
        print(f'Admin user created: {admin_email}')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)