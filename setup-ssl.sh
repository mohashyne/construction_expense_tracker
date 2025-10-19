#!/bin/bash

# SSL setup script for Construction Expense Tracker
# This script sets up Let's Encrypt SSL certificates

set -e

DOMAIN=${1:-""}
EMAIL=${2:-""}

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

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    print_error "Usage: ./setup-ssl.sh <domain> <email>"
    print_warning "Example: ./setup-ssl.sh example.com admin@example.com"
    exit 1
fi

print_status "Setting up SSL for $DOMAIN with email $EMAIL"

# Check if certbot is installed
if ! command -v certbot &> /dev/null; then
    print_status "Installing Certbot..."
    sudo apt update
    sudo apt install -y certbot python3-certbot-nginx
fi

# Stop nginx temporarily
print_status "Stopping nginx temporarily..."
docker-compose stop nginx

# Generate certificates
print_status "Generating SSL certificates..."
sudo certbot certonly --standalone \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN" \
    -d "www.$DOMAIN"

# Create SSL directory
print_status "Setting up SSL directory..."
mkdir -p ssl/

# Copy certificates
print_status "Copying certificates..."
sudo cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ssl/
sudo cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" ssl/

# Set proper permissions
sudo chown $(whoami):$(whoami) ssl/*.pem
chmod 644 ssl/fullchain.pem
chmod 600 ssl/privkey.pem

# Update nginx configuration
print_status "Updating nginx configuration..."
sed -i "s/server_name _;/server_name $DOMAIN www.$DOMAIN;/" nginx.conf

# Restart nginx
print_status "Starting nginx with SSL..."
docker-compose up -d nginx

# Test SSL
print_status "Testing SSL configuration..."
sleep 5

if curl -f "https://$DOMAIN/health/" > /dev/null 2>&1; then
    print_status "SSL setup completed successfully!"
    print_status "Your site is now available at https://$DOMAIN"
else
    print_warning "SSL setup completed but health check failed"
    print_warning "Check nginx logs: docker-compose logs nginx"
fi

# Setup auto-renewal
print_status "Setting up auto-renewal..."
(crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet && docker-compose restart nginx") | crontab -

print_status "Auto-renewal cron job added"

echo ""
echo "🎉 SSL Setup Complete!"
echo "📋 Next steps:"
echo "1. Update your .env file with ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN"
echo "2. Update CORS_ALLOWED_ORIGINS=https://$DOMAIN,https://www.$DOMAIN"
echo "3. Test your site: https://$DOMAIN"
echo "4. Check SSL rating: https://www.ssllabs.com/ssltest/"

echo ""
print_warning "Certificate will auto-renew. Check with: sudo certbot certificates"
