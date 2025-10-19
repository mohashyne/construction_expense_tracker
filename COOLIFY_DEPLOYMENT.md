# 🚀 Coolify Deployment Guide - GitHub Integration

Complete guide for deploying Construction Expense Tracker on Coolify using GitHub repository.

## 📋 Prerequisites

- Coolify installed on your Contabo VPS
- GitHub repository (already set up: `mohashyne/construction_expense_tracker`)
- Domain name pointing to your Contabo server
- Coolify dashboard access

## 🔧 Step-by-Step Deployment

### Step 1: Access Coolify Dashboard

1. Open your Coolify dashboard (usually at `https://your-server-ip:8000` or your domain)
2. Log in with your Coolify credentials

### Step 2: Create New Application

1. **Click "New Project"** or "+" to create a new application
2. **Select "Git Repository"** as the source
3. **Choose "GitHub"** as the Git provider

### Step 3: Connect GitHub Repository

1. **Repository URL**: `https://github.com/mohashyne/construction_expense_tracker`
2. **Branch**: `main`
3. **Build Pack**: Select "Docker" or "Docker Compose"
4. **Docker Compose File**: `docker-compose.coolify.yml`

### Step 4: Configure Environment Variables

Add these **REQUIRED** environment variables in Coolify:

```bash
# Core Django Settings (REQUIRED)
SECRET_KEY=your-new-generated-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# Database Settings (REQUIRED)
POSTGRES_PASSWORD=your-strong-database-password
DATABASE_URL=postgresql://postgres:your-strong-database-password@postgres:5432/construction_tracker

# Site Configuration (REQUIRED)
SITE_URL=https://your-domain.com
CORS_ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com

# Email Settings (OPTIONAL but recommended)
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@your-domain.com
ADMIN_EMAILS=admin@your-domain.com

# Security Settings (OPTIONAL - defaults are secure)
SECURE_SSL_REDIRECT=True
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SECURE=True
```

### Step 5: Generate Secret Key

Use this command to generate a secure Django secret key:

```bash
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

Or use an online generator: https://djecrety.ir/

### Step 6: Configure Domain

1. **In Coolify Dashboard**:
   - Go to your application settings
   - Add your domain name
   - Enable SSL/HTTPS (Let's Encrypt)
   - Set up automatic SSL renewal

2. **DNS Configuration**:
   - Point your domain A record to your Contabo server IP
   - Add CNAME for `www` subdomain

### Step 7: Deploy Application

1. **Click "Deploy"** in Coolify
2. **Monitor the build logs** for any issues
3. **Wait for deployment to complete** (usually 5-10 minutes)

### Step 8: Post-Deployment Setup

Once deployed, run these commands in Coolify's application console:

```bash
# Run database migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Create super owner account
python manage.py create_super_owner --username admin --email admin@your-domain.com
```

## 🔍 Verification

### Health Check
Visit: `https://your-domain.com/health/`
Should return: `{"status": "healthy", "timestamp": ...}`

### Application Access
- **Main App**: `https://your-domain.com`
- **Admin Panel**: `https://your-domain.com/admin/`
- **Super Owner Dashboard**: `https://your-domain.com/super-owner/`

## 🎯 Coolify Configuration Options

### Build Configuration
```yaml
Build Command: docker-compose -f docker-compose.coolify.yml build
Start Command: docker-compose -f docker-compose.coolify.yml up -d
Health Check: /health/
Port: 8000
```

### Service Configuration
The `docker-compose.coolify.yml` includes:
- **Django App** (main application)
- **PostgreSQL** (database)
- **Redis** (caching and sessions)

### Auto-Deployment
Enable **automatic deployments** on git push:
1. Go to application settings in Coolify
2. Enable "Auto Deploy on Git Push"
3. Set up webhook (Coolify will provide the URL)
4. Add webhook to your GitHub repository

## 🔧 Environment Variables Reference

### Required Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | `your-50-char-secret-key` |
| `POSTGRES_PASSWORD` | Database password | `super-secure-password-123` |
| `ALLOWED_HOSTS` | Allowed domains | `yourdomain.com,www.yourdomain.com` |
| `SITE_URL` | Full site URL | `https://yourdomain.com` |

### Optional Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `False` | Debug mode |
| `EMAIL_HOST_USER` | - | SMTP username |
| `EMAIL_HOST_PASSWORD` | - | SMTP password |
| `REDIS_URL` | `redis://redis:6379/1` | Redis connection |

## 🔄 Updates and Maintenance

### Automatic Updates
With auto-deploy enabled, simply:
```bash
git push origin main
```
Coolify will automatically redeploy your application.

### Manual Updates
1. Go to your application in Coolify
2. Click "Deploy" to redeploy latest code
3. Monitor deployment logs

### Database Migrations
After code updates that include model changes:
```bash
# In Coolify console
python manage.py migrate
```

## 🐛 Troubleshooting

### Common Issues

1. **Build Fails**
   - Check build logs in Coolify
   - Verify `docker-compose.coolify.yml` syntax
   - Ensure all required environment variables are set

2. **Application Won't Start**
   - Check if PostgreSQL is running
   - Verify `DATABASE_URL` format
   - Check application logs

3. **Database Connection Issues**
   - Verify `POSTGRES_PASSWORD` matches in all services
   - Check if PostgreSQL container is healthy
   - Ensure database name matches

4. **Static Files Not Loading**
   - Run `python manage.py collectstatic --noinput`
   - Check volume mounts in docker-compose

### Debugging Commands
```bash
# View application logs
docker-compose -f docker-compose.coolify.yml logs app

# Check database connection
docker-compose -f docker-compose.coolify.yml exec app python manage.py dbshell

# Run Django shell
docker-compose -f docker-compose.coolify.yml exec app python manage.py shell

# Check health status
curl https://your-domain.com/health/
```

## 🔒 Security Checklist

Before going live, ensure:

- [ ] `DEBUG=False` in production
- [ ] Strong `SECRET_KEY` generated
- [ ] Strong database password set
- [ ] `ALLOWED_HOSTS` properly configured
- [ ] SSL certificate active
- [ ] Email notifications configured
- [ ] Regular backups scheduled in Coolify
- [ ] Monitoring set up

## 📊 Monitoring

### Health Endpoints
- `/health/` - Basic health check
- `/health/detailed/` - Detailed system health
- `/ready/` - Readiness probe
- `/alive/` - Liveness probe

### Coolify Monitoring
Coolify provides built-in monitoring for:
- Application uptime
- Resource usage (CPU, Memory)
- Response times
- Error rates

## 📞 Support

### If deployment fails:
1. Check Coolify build/deployment logs
2. Verify all environment variables are correct
3. Ensure GitHub repository is accessible
4. Check domain DNS configuration

### Application issues:
1. Check application health: `/health/detailed/`
2. Review application logs in Coolify
3. Verify database connectivity
4. Check static file serving

---

## 🎉 Success!

Once deployed successfully, your Construction Expense Tracker will be available at your domain with:

✅ **Secure HTTPS** with automatic SSL certificates  
✅ **Production-grade** PostgreSQL database  
✅ **Redis caching** for optimal performance  
✅ **Health monitoring** and auto-recovery  
✅ **Automatic deployments** on git push  
✅ **Multi-tenant architecture** ready to use  

Your application is now ready for production use! 🚀
