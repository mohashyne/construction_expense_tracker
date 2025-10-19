#!/bin/bash

# Production deployment script for Construction Expense Tracker
# Usage: ./deploy.sh [environment]

set -e  # Exit on any error

ENVIRONMENT=${1:-production}
PROJECT_NAME="construction-expense-tracker"

echo "🚀 Starting deployment for $ENVIRONMENT environment..."

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if .env file exists
if [ ! -f .env ]; then
    print_error ".env file not found! Please create it from .env.example"
    print_warning "Run: cp .env.example .env"
    print_warning "Then edit .env with your production settings"
    exit 1
fi

print_status "Environment file found"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running! Please start Docker and try again."
    exit 1
fi

print_status "Docker is running"

# Pull latest changes (if this is a git deployment)
if [ -d .git ]; then
    print_status "Pulling latest changes..."
    git pull origin main || {
        print_warning "Failed to pull latest changes, continuing with current version"
    }
fi

# Build and start services
print_status "Building Docker images..."
docker-compose build --no-cache

print_status "Starting services..."
docker-compose up -d

# Wait for database to be ready
print_status "Waiting for database to be ready..."
sleep 10

# Run database migrations
print_status "Running database migrations..."
docker-compose exec -T web python manage.py migrate

# Collect static files
print_status "Collecting static files..."
docker-compose exec -T web python manage.py collectstatic --noinput

# Create superuser if it doesn't exist
print_status "Checking for super owner..."
docker-compose exec -T web python manage.py shell -c "
from core.models import User, SuperOwner
if not SuperOwner.objects.exists():
    print('No super owner found. Please create one manually using:')
    print('docker-compose exec web python manage.py create_super_owner --username admin --email admin@example.com')
else:
    print('Super owner already exists')
" || print_warning "Could not check super owner status"

# Health check
print_status "Performing health check..."
sleep 5

if curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
    print_status "Application is healthy!"
else
    print_error "Health check failed!"
    print_warning "Check logs with: docker-compose logs web"
fi

print_status "Deployment completed!"
print_status "Application should be available at http://localhost:8000"
print_warning "Don't forget to configure SSL certificates for production!"

echo ""
echo "📋 Next steps:"
echo "1. Configure your domain DNS to point to this server"
echo "2. Set up SSL certificates (Let's Encrypt recommended)"
echo "3. Update ALLOWED_HOSTS in your .env file"
echo "4. Configure email settings for notifications"
echo "5. Set up regular backups"

echo ""
echo "🔧 Useful commands:"
echo "  View logs: docker-compose logs -f"
echo "  Restart services: docker-compose restart"
echo "  Stop services: docker-compose down"
echo "  Update application: ./deploy.sh"
