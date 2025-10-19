#!/bin/bash

# Construction Expense Tracker - Startup Script
echo "🏗️  Construction Expense Tracker Setup"
echo "======================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📋 Installing dependencies..."
pip install -r requirements.txt

# Run migrations
echo "💾 Running database migrations..."
python manage.py migrate

# Create superuser if it doesn't exist
echo "👤 Checking for admin user..."
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Admin user created: admin/admin123')
else:
    print('Admin user already exists')
"

# Collect static files
echo "🎨 Collecting static files..."
python manage.py collectstatic --noinput

echo ""
echo "✅ Setup completed!"
echo ""
echo "🚀 To start the server:"
echo "   python manage.py runserver"
echo ""
echo "🌐 Then visit:"
echo "   Application: http://127.0.0.1:8000/"
echo "   Admin:       http://127.0.0.1:8000/admin/"
echo ""
echo "🔑 Admin credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "📚 For more information, see README.md"
