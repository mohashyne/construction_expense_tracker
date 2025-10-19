# Construction Expense Tracker - Production Deployment Guide

## 🚀 Deployment on Coolify/Contabo

This guide covers deploying the Construction Expense Tracker on Coolify (self-hosted PaaS) running on Contabo VPS.

## 📋 Prerequisites

- Contabo VPS with at least 2GB RAM, 2 CPU cores
- Docker and Docker Compose installed
- Coolify installed and configured
- Domain name pointing to your server

## 🔐 Security Setup (CRITICAL)

### 1. Fix Secret Exposure Issue

The security incident was caused by the `.env` file being committed to git. This has been resolved:

- ✅ `.env` file removed from git tracking
- ✅ `.gitignore` updated to prevent future commits
- ✅ `.env.example` created as template

### 2. Generate New Secrets

```bash
# Generate a new Django secret key
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Generate strong PostgreSQL password
openssl rand -base64 32
```

## 🛠️ Quick Deployment (Recommended)

### Step 1: Clone and Setup

```bash
# Clone the repository
git clone <your-repository-url>
cd construction_expense_tracker

# Create environment file from template
cp .env.example .env

# Edit with your production settings
nano .env
```

### Step 2: Configure Environment Variables

Edit `.env` with your production values:

```bash
# Required settings
SECRET_KEY=your-new-generated-secret-key
DEBUG=False
DATABASE_URL=postgresql://postgres:your-strong-password@db:5432/construction_tracker
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# Email settings
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Security settings
SECURE_SSL_REDIRECT=True
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SECURE=True
```

### Step 3: Deploy

```bash
# Make deployment script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh production
```

## 🌐 Coolify Deployment

### Option 1: Docker Compose (Recommended)

1. **Create new project in Coolify**
   - Go to Coolify dashboard
   - Create new project
   - Choose "Docker Compose" option

2. **Upload docker-compose.yml**
   - Copy the contents of `docker-compose.yml`
   - Paste into Coolify's compose editor
   - Add environment variables in Coolify UI

3. **Environment Variables in Coolify**
   ```
   SECRET_KEY=your-new-secret-key
   DEBUG=False
   DATABASE_URL=postgresql://postgres:secure_password@db:5432/construction_tracker
   ALLOWED_HOSTS=your-domain.com
   CORS_ALLOWED_ORIGINS=https://your-domain.com
   SITE_URL=https://your-domain.com
   # ... add all variables from .env.example
   ```

4. **Deploy**
   - Click "Deploy" in Coolify
   - Monitor deployment logs

### Option 2: Git Repository

1. **Connect Repository**
   - Add your git repository to Coolify
   - Set build pack to "Docker"
   - Point to `Dockerfile`

2. **Configure Build**
   - Build command: `docker build -t app .`
   - Start command: `gunicorn --bind 0.0.0.0:8000 construction_tracker.wsgi:application`

3. **Add Services**
   - PostgreSQL database
   - Redis for caching
   - Set up service connections

## 🔧 Manual Server Setup (Alternative)

### Step 1: Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login again for group changes to take effect
```

### Step 2: Application Setup

```bash
# Clone repository
git clone <your-repository-url>
cd construction_expense_tracker

# Setup environment
cp .env.example .env
nano .env  # Edit with production values

# Deploy
./deploy.sh production
```

### Step 3: SSL Setup with Let's Encrypt

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Generate certificates
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Auto-renewal (crontab)
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 🔒 Security Configuration

### Firewall Setup

```bash
# UFW firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw status
```

### SSL Configuration

Place your SSL certificates in the `ssl/` directory:

```bash
mkdir -p ssl/
# Copy your certificates
cp /path/to/fullchain.pem ssl/
cp /path/to/privkey.pem ssl/
```

## 📊 Monitoring and Maintenance

### Health Checks

The application includes built-in health check endpoints:

- `GET /health/` - Basic health check
- `GET /health/detailed/` - Database and cache checks
- `GET /ready/` - Readiness probe
- `GET /alive/` - Liveness probe

### Log Management

```bash
# View application logs
docker-compose logs -f web

# View all service logs
docker-compose logs -f

# View specific service
docker-compose logs -f nginx
docker-compose logs -f db
```

### Database Backups

```bash
# Create backup
docker-compose exec db pg_dump -U postgres construction_tracker > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
docker-compose exec -T db psql -U postgres construction_tracker < backup_file.sql
```

## 🔄 Updates and Maintenance

### Application Updates

```bash
# Pull latest changes
git pull origin main

# Redeploy
./deploy.sh production
```

### Database Maintenance

```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Create super owner
docker-compose exec web python manage.py create_super_owner --username admin --email admin@example.com
```

## 🐛 Troubleshooting

### Common Issues

1. **Health check fails**
   ```bash
   # Check application logs
   docker-compose logs web
   
   # Check if database is ready
   docker-compose exec db pg_isready -U postgres
   ```

2. **Database connection issues**
   ```bash
   # Restart database
   docker-compose restart db
   
   # Check database logs
   docker-compose logs db
   ```

3. **Static files not loading**
   ```bash
   # Recollect static files
   docker-compose exec web python manage.py collectstatic --noinput
   
   # Restart nginx
   docker-compose restart nginx
   ```

### Emergency Commands

```bash
# Stop all services
docker-compose down

# Remove all containers and volumes (DESTRUCTIVE)
docker-compose down -v

# Rebuild everything
docker-compose build --no-cache
docker-compose up -d
```

## 📈 Performance Optimization

### Database Optimization

```bash
# Database tuning (add to .env)
POSTGRES_INITDB_ARGS=--data-checksums
POSTGRES_CONFIG=max_connections=100,shared_buffers=256MB
```

### Caching

Redis is included for caching and sessions:

```bash
# Monitor Redis
docker-compose exec redis redis-cli monitor

# Clear cache
docker-compose exec redis redis-cli flushall
```

## 🚨 Security Checklist

- [ ] New SECRET_KEY generated
- [ ] DEBUG=False in production
- [ ] Strong database passwords
- [ ] SSL certificates configured
- [ ] Firewall rules applied
- [ ] Regular backups scheduled
- [ ] Monitoring set up
- [ ] Error tracking configured (Sentry)
- [ ] Environment variables secured
- [ ] Domain properly configured

## 📞 Support

For deployment issues:

1. Check application logs: `docker-compose logs -f`
2. Verify health endpoints: `curl http://localhost:8000/health/`
3. Review this deployment guide
4. Check Coolify documentation for platform-specific issues

## 🔗 Useful Links

- [Coolify Documentation](https://coolify.io/docs)
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/)
- [Let's Encrypt](https://letsencrypt.org/)

---

**Note**: Always test deployments in a staging environment before deploying to production!
