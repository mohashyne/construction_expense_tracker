# 🚀 Quick Deploy to Coolify

Deploy Construction Expense Tracker to Coolify in under 10 minutes!

## ⚡ Quick Start

### 1. Repository Setup ✅
Your GitHub repo is ready: `https://github.com/mohashyne/construction_expense_tracker`

### 2. Generate Secret Key
```bash
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### 3. Deploy in Coolify

1. **New Application** → **Git Repository** → **GitHub**
2. **Repository**: `mohashyne/construction_expense_tracker`
3. **Branch**: `main`
4. **Build Pack**: `Docker Compose`
5. **Compose File**: `docker-compose.coolify.yml`

### 4. Environment Variables (Copy & Paste)

```bash
# REQUIRED - Replace with your values
SECRET_KEY=your-generated-secret-key-from-step-2
POSTGRES_PASSWORD=your-strong-database-password
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
SITE_URL=https://your-domain.com
CORS_ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com

# OPTIONAL - For email notifications
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@your-domain.com
ADMIN_EMAILS=admin@your-domain.com

# These have secure defaults (optional)
DEBUG=False
SECURE_SSL_REDIRECT=True
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SECURE=True
```

### 5. Deploy & Wait
Click **Deploy** and wait 5-10 minutes. ☕

### 6. Post-Deployment (One-time setup)
In Coolify's application console, run:
```bash
python manage.py create_super_owner --username admin --email admin@your-domain.com
```

## ✅ Verification

- **Health Check**: `https://your-domain.com/health/`
- **Application**: `https://your-domain.com`
- **Admin Panel**: `https://your-domain.com/super-owner/`

## 🔄 Auto-Deploy Setup

1. In Coolify → Your App → **Settings**
2. Enable **"Auto Deploy on Git Push"**
3. Copy webhook URL
4. Add to GitHub repo: **Settings** → **Webhooks** → **Add webhook**

Now every `git push` will auto-deploy! 🎉

## 📋 What You Get

✅ **Multi-tenant** construction project management  
✅ **PostgreSQL** database with backups  
✅ **Redis** caching for performance  
✅ **SSL certificates** (Let's Encrypt)  
✅ **Health monitoring** built-in  
✅ **Auto-deployments** on code changes  
✅ **Production security** pre-configured  

## 🚨 Need Help?

1. **Build fails?** → Check build logs in Coolify
2. **App won't start?** → Verify all environment variables set
3. **Database issues?** → Check `POSTGRES_PASSWORD` matches everywhere
4. **Domain issues?** → Verify DNS A record points to your server

## 📖 Full Documentation

- **Complete guide**: `COOLIFY_DEPLOYMENT.md`
- **General deployment**: `DEPLOYMENT.md`
- **Application guide**: `README.md`

---

🎯 **Your Construction Expense Tracker will be live in minutes!**
