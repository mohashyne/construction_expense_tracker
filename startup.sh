#!/bin/bash

# Production startup script for Construction Expense Tracker
# This script runs after deployment to initialize the application

set -e

echo "🚀 Initializing Construction Expense Tracker..."

# Wait for database to be ready
echo "⏳ Waiting for database..."
while ! python manage.py dbshell --command="SELECT 1;" > /dev/null 2>&1; do
    echo "Database not ready, waiting..."
    sleep 2
done
echo "✅ Database is ready"

# Run migrations
echo "📊 Running database migrations..."
python manage.py migrate --noinput

# Create logs directory
echo "📝 Setting up logging..."
mkdir -p logs/
touch logs/construction_tracker.log
touch logs/errors.log

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Create super owner if it doesn't exist
echo "👤 Checking for super owner..."
python manage.py shell -c "
import os
from core.models import SuperOwner, User
if not SuperOwner.objects.exists():
    print('Creating super owner...')
    # You can create it manually later using the management command
    print('Run: python manage.py create_super_owner --username admin --email admin@example.com')
else:
    print('Super owner already exists')
"

# Create sample data if in development
if [ "${DEBUG:-False}" = "True" ]; then
    echo "🧪 Creating test data (development mode)..."
    python manage.py shell -c "
from core.models import User
if not User.objects.filter(username='testuser').exists():
    print('Creating test user...')
else:
    print('Test user already exists')
" || echo "Could not create test data"
fi

echo "✅ Initialization complete!"
echo ""
echo "🎉 Construction Expense Tracker is ready!"
echo "📍 Health check: curl http://localhost:8000/health/"
echo "🌐 Access your app at the configured domain"

# Keep container running
exec "$@"
