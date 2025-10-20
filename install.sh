#!/bin/bash

# Enterprise Wiki Installation Script
# This script sets up the Enterprise Wiki system

set -e

echo "🚀 Enterprise Wiki Installation Script"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python is installed
check_python() {
    print_status "Checking Python installation..."
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        print_status "Python $PYTHON_VERSION found"

        # Check if version is >= 3.8
        if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)'; then
            print_status "Python version is compatible"
        else
            print_error "Python 3.8 or higher is required"
            exit 1
        fi
    else
        print_error "Python 3 is not installed"
        exit 1
    fi
}

# Create virtual environment
create_venv() {
    print_status "Creating virtual environment..."
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_status "Virtual environment created"
    else
        print_warning "Virtual environment already exists"
    fi
}

# Activate virtual environment
activate_venv() {
    print_status "Activating virtual environment..."
    source venv/bin/activate
    print_status "Virtual environment activated"
}

# Install dependencies
install_dependencies() {
    print_status "Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    print_status "Dependencies installed"
}

# Setup environment file
setup_env() {
    print_status "Setting up environment configuration..."
    if [ ! -f ".env" ]; then
        cp .env.example .env
        print_status "Created .env file from template"
        print_warning "Please edit .env file with your configuration"
    else
        print_warning ".env file already exists"
    fi
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    mkdir -p logs
    mkdir -p backups
    mkdir -p app/static/uploads
    mkdir -p search_index
    print_status "Directories created"
}

# Set up database
setup_database() {
    print_status "Setting up database..."

    # Export Flask app
    export FLASK_APP=run.py

    # Initialize database
    if python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all(); print('Database tables created')" 2>/dev/null; then
        print_status "Database initialized successfully"
    else
        print_error "Failed to initialize database"
        exit 1
    fi

    # Deploy initial data
    if python -c "from run import deploy; import os; os.environ['FLASK_APP'] = 'run.py'; deploy()" 2>/dev/null; then
        print_status "Initial data deployed successfully"
    else
        print_warning "Failed to deploy initial data (this might be normal if data already exists)"
    fi
}

# Set file permissions
set_permissions() {
    print_status "Setting file permissions..."
    chmod 755 app/static/uploads
    chmod 644 .env
    print_status "Permissions set"
}

# Create systemd service file (optional)
create_systemd_service() {
    if command -v systemctl &> /dev/null; then
        read -p "Do you want to create a systemd service file? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            CURRENT_DIR=$(pwd)
            SERVICE_FILE="/etc/systemd/system/enterprise-wiki.service"

            sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=Enterprise Wiki
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$CURRENT_DIR
Environment="PATH=$CURRENT_DIR/venv/bin"
ExecStart=$CURRENT_DIR/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 run:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

            sudo systemctl daemon-reload
            print_status "Systemd service file created at $SERVICE_FILE"
            print_warning "Remember to update the User and Group fields if needed"
        fi
    fi
}

# Run installation test
run_test() {
    print_status "Running basic installation test..."

    # Test basic import
    if python -c "from app import create_app; app = create_app(); print('App creation successful')" 2>/dev/null; then
        print_status "✅ Application imports successfully"
    else
        print_error "❌ Application import failed"
        return 1
    fi

    # Test database connection
    if python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.session.execute('SELECT 1'); print('Database connection successful')" 2>/dev/null; then
        print_status "✅ Database connection successful"
    else
        print_error "❌ Database connection failed"
        return 1
    fi

    print_status "✅ Installation test completed successfully"
}

# Print next steps
print_next_steps() {
    echo ""
    echo "🎉 Installation completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Edit the .env file with your configuration"
    echo "2. Run the application:"
    echo "   source venv/bin/activate"
    echo "   python run.py"
    echo "3. Open http://localhost:5000 in your browser"
    echo "4. Login with admin@company.com / admin123 (change immediately!)"
    echo ""
    echo "For production deployment:"
    echo "- Use a proper WSGI server like Gunicorn"
    echo "- Configure HTTPS"
    echo "- Set up a reverse proxy (Nginx/Apache)"
    echo "- Configure regular backups"
    echo ""
    echo "Documentation: README.md"
    echo "Support: Check the logs in logs/ directory"
}

# Main installation flow
main() {
    echo "Starting Enterprise Wiki installation..."
    echo ""

    check_python
    create_venv
    activate_venv
    install_dependencies
    setup_env
    create_directories
    setup_database
    set_permissions
    create_systemd_service

    echo ""
    if run_test; then
        print_next_steps
    else
        print_error "Installation test failed. Please check the error messages above."
        exit 1
    fi
}

# Handle script interruption
trap 'print_warning "Installation interrupted"; exit 1' INT

# Check if running as root (not recommended)
if [ "$EUID" -eq 0 ]; then
    print_warning "Running as root is not recommended"
    read -p "Do you want to continue? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Run main installation
main

echo ""
echo "Installation script completed. 🎊"