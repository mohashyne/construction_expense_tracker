# Super Owner & Admin System Guide

This guide covers the complete super owner (app owner) and Django admin system for ConstructPro.

## Quick Start for App Owners

### 1. Create Your First Super Owner
```bash
cd /Users/muhammadibnsalyhu/Desktop/construction_expense_tracker
python manage.py create_superowner --primary --full-access
```

### 2. Access Your Admin Interfaces
- **Super Owner Dashboard:** http://127.0.0.1:8000/super-owner/
- **Registration Management:** http://127.0.0.1:8000/admin/activation-requests/
- **Django Admin:** http://127.0.0.1:8000/admin/
- **Login Page:** http://127.0.0.1:8000/login/

## System Architecture

### Access Hierarchy
1. **Super Owners** - App owners with system-wide control
2. **Django Admin** - Technical administrative interface  
3. **Company Admins** - Company-level management
4. **Staff/Users** - Standard application users

### Super Owner Types

**Primary Owner**
- Cannot be revoked - Permanent access
- Full system control - All permissions enabled
- Can delegate permissions to other super owners
- Only one per system

**Delegated Super Owners**
- Configurable permissions based on delegation level
- Can be revoked by primary owner
- Role-based access to specific functions

## Core Features

### Registration Approval System
- **Document Upload & Review** - Users upload required documents
- **Multi-Step Approval** - Pending → Under Review → Approved/Rejected
- **Email Notifications** - Automated emails at each stage
- **Secure Document Storage** - Protected file access

### Super Owner Dashboard
- **Statistics Overview** - Pending requests, approvals, companies
- **Recent Activity** - Latest registration requests
- **Quick Actions** - Direct links to common tasks
- **Permission Summary** - Your current access level

### Django Admin Integration
- **Enhanced User Management** - Extended profiles and permissions
- **Company Administration** - Full company lifecycle management
- **Document Management** - View and approve uploaded files
- **Audit Trail** - Track all administrative actions

## Creating Super Owners

### Method 1: Management Command (Recommended)
```bash
# Interactive creation with prompts
python manage.py create_superowner

# Non-interactive with full arguments
python manage.py create_superowner \
    --username=admin \
    --email=admin@company.com \
    --first-name=Admin \
    --last-name=User \
    --primary \
    --full-access
```

### Method 2: Django Admin
1. Login to Django admin at `/admin/`
2. Go to Users → Add User
3. Create the user account
4. Edit the user and add Super Owner access via inline

### Method 3: Django Shell
```python
python manage.py shell

from django.contrib.auth.models import User
from core.models import SuperOwner, UserProfile

# Create user account
user = User.objects.create_user(
    username='superowner',
    email='admin@company.com',  
    first_name='Super',
    last_name='Owner',
    password='secure_password123',
    is_staff=True  # Required for Django admin
)

# Create user profile
profile = UserProfile.objects.create(
    user=user,
    is_account_active=True,
    is_verified=True,
    account_type='individual'
)

# Create super owner with full permissions
super_owner = SuperOwner.objects.create(
    user=user,
    is_primary_owner=True,
    can_activate_accounts=True,
    can_manage_companies=True,
    can_manage_users=True,
    can_access_django_admin=True,
    can_delegate_permissions=True,
    can_manage_billing=True,
    can_view_system_analytics=True
)

print(f"Super Owner created: {user.username}")
```

## Permission System

### Available Permissions

| Permission | Description | Required For |
|------------|-------------|--------------|
| `can_activate_accounts` | Approve/reject registration requests | Registration management |
| `can_manage_companies` | Create, edit, delete companies | Company oversight |
| `can_manage_users` | Manage all user accounts | User administration |
| `can_access_django_admin` | Access Django admin interface | Technical management |
| `can_delegate_permissions` | Create/manage other super owners | Team management |
| `can_manage_billing` | Handle subscriptions and billing | Financial oversight |
| `can_view_system_analytics` | Access reports and analytics | Business intelligence |

### Permission Matrix

| User Type | Registration | Companies | Users | Django Admin | Delegation | Billing | Analytics |
|-----------|-------------|-----------|-------|--------------|------------|---------|-----------|
| Primary Owner | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Full Access | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| Company Manager | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ | ✅ |
| User Manager | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Read Only | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |

## Registration Approval Workflow

### Step 1: Registration Submitted
- User fills out registration form
- Uploads required documents (business cert, ID, etc.)
- System creates `AccountActivationRequest`
- Email notifications sent to super owners

### Step 2: Initial Review
- Super owner receives email notification
- Logs into admin dashboard
- Reviews application details and documents
- Can mark as "Under Review" to claim it

### Step 3: Document Verification  
- Each document reviewed individually
- Can approve, reject, or request revision
- Comments added for feedback
- Additional documents can be requested

### Step 4: Final Decision
**Approve:**
- Creates user account with generated password
- Sets up company (if company registration)
- Sends welcome email with login credentials

**Reject:**
- Sends rejection email with reason
- User can submit new request if desired

**Request Documents:**
- Sends email requesting additional documentation
- User can upload more documents

### Step 5: Post-Approval
- User logs in and changes password
- Company setup and role assignment
- Staff/users can be invited by company owner

## Access URLs & Features

### Super Owner Dashboard (`/super-owner/`)
- **Statistics Cards** - Pending requests, approvals, companies
- **Recent Requests Table** - Latest 10 registration requests  
- **Quick Action Buttons** - Direct links to common tasks
- **Permission Summary** - Your current access capabilities

### Registration Management (`/admin/activation-requests/`)
- **Request Filtering** - By status, type, date
- **Bulk Actions** - Approve/reject multiple requests
- **Document Viewer** - Secure document preview/download
- **Email Integration** - Send messages directly to applicants

### Request Detail (`/admin/activation-requests/{id}/`)
- **Complete Application View** - All submitted information
- **Document Gallery** - All uploaded files with status
- **Action Panel** - Approve, reject, request documents
- **Contact Integration** - Direct email and phone links

### Django Admin (`/admin/`)
- **User Management** - Enhanced user profiles and permissions
- **Company Administration** - Complete company lifecycle
- **Super Owner Management** - Delegate and revoke permissions  
- **System Configuration** - Technical settings and logs

## Login & Authentication

### Regular Users
- Login at `/login/` with email or username
- Account must be approved by super owner
- Pending accounts cannot login

### Super Owners
- Same login page with "Super Owner Access" link
- Dashboard shows after login if super owner
- Django admin accessible if permission granted

### Security Features
- **Email/Username Flexibility** - Login with either
- **Account Activation Required** - All accounts need approval
- **Permission-Based Access** - Features shown based on permissions
- **Audit Trail** - All actions logged with timestamps

## Document Management

### Supported File Types
- **PDF** - Preferred for official documents
- **Images** - JPG, PNG for photos of documents
- **Size Limit** - 10MB per file

### Document Types

**Company Registration:**
- Business Registration Certificate (required)
- Director/Owner ID Document (required)  
- Tax Registration Certificate (optional)
- CAC Certificate (optional)
- Utility Bill for address proof (optional)

**Individual Registration:**
- Government ID Document (required)
- Passport (optional)
- Professional License (optional)

### Document Security
- **Protected Access** - Only super owners can view
- **Secure Storage** - Files stored outside web root
- **Download Tracking** - Audit trail of file access

## Email System

### Automated Notifications

**Registration Submitted:**
```
Subject: New Registration Request - [Type]
To: All super owners with activation permissions
Content: Basic info + admin panel link
```

**Status Updates:**
- **Approved** - Welcome email with login credentials
- **Rejected** - Rejection notice with reason
- **Documents Required** - Request for additional files

**User Invitations:**
- **Existing Users** - Invitation to join company
- **New Users** - Welcome email with generated credentials

### Email Configuration
```python
# Add to settings.py or .env
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'  
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'noreply@yourcompany.com'
SITE_URL = 'https://yoursite.com'  # Used in email links
```

## Troubleshooting

### Cannot Access Django Admin
**Problem:** 403 Forbidden or login loop
**Solutions:**
1. Verify user has `is_staff=True`
2. Check super owner has `can_access_django_admin=True`  
3. Ensure UserProfile exists and is active

```python
# Fix via shell
user = User.objects.get(username='yourusername')
user.is_staff = True
user.save()

profile, created = UserProfile.objects.get_or_create(user=user)
profile.is_account_active = True
profile.save()
```

### Registration Emails Not Sending
**Problem:** Users not receiving notifications
**Solutions:**
1. Check email configuration in settings
2. Verify SITE_URL setting
3. Test email connectivity
4. Check spam/junk folders

```bash
# Test email in shell
python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail('Test', 'Test message', 'from@example.com', ['to@example.com'])
```

### Permission Denied Errors
**Problem:** "You don't have permission to access this"
**Solutions:**
1. Verify user is super owner
2. Check specific permission for the action
3. Ensure super owner profile exists

```python
# Check permissions in shell
user = User.objects.get(username='yourusername')
print(f"Has super owner profile: {hasattr(user, 'super_owner_profile')}")
if hasattr(user, 'super_owner_profile'):
    so = user.super_owner_profile
    print(f"Can activate accounts: {so.can_activate_accounts}")
    print(f"Can access admin: {so.can_access_django_admin}")
```

### Documents Not Uploading
**Problem:** File upload fails or files not accessible
**Solutions:**
1. Check file size (max 10MB)
2. Verify file format (PDF, JPG, PNG)
3. Check media settings in Django
4. Ensure media directory is writable

```python
# Check media settings
from django.conf import settings
print(f"MEDIA_URL: {settings.MEDIA_URL}")
print(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
```

## Maintenance & Monitoring

### Regular Tasks
- **Clean expired requests** (older than 30 days)
- **Monitor email deliverability** 
- **Review super owner permissions**
- **Backup uploaded documents**

### Cleanup Commands
```bash
# Clean expired activation requests
python manage.py shell -c "
from core.models import AccountActivationRequest
from django.utils import timezone
from datetime import timedelta

expired = AccountActivationRequest.objects.filter(
    expires_at__lt=timezone.now(),
    status='pending'
)
print(f'Found {expired.count()} expired requests')
expired.update(status='expired')
"
```

### Monitoring Queries
```python
# Check system health
from core.models import *
from django.utils import timezone

print("=== SYSTEM OVERVIEW ===")
print(f"Total companies: {Company.objects.filter(is_active=True).count()}")
print(f"Total users: {User.objects.filter(is_active=True).count()}")
print(f"Super owners: {SuperOwner.objects.count()}")

print("\n=== PENDING REQUESTS ===")
pending = AccountActivationRequest.objects.filter(status='pending')
print(f"Pending registrations: {pending.count()}")
for req in pending:
    print(f"  - {req.email} ({req.get_request_type_display()}) - {req.created_at.strftime('%Y-%m-%d')}")
```

## Best Practices

### Security
1. **Use strong passwords** for super owner accounts
2. **Enable 2FA** if available (future enhancement)
3. **Regular permission audits** - Review who has what access
4. **Limit delegation** - Don't give everyone full permissions

### Operations
1. **Respond quickly** to registration requests (24-48 hours)
2. **Document decisions** - Use notes field for approval/rejection reasons
3. **Monitor email delivery** - Check bounce rates and spam issues
4. **Backup regularly** - Include documents and database

### Delegation
1. **Principle of least privilege** - Give minimum needed permissions
2. **Role-based assignment** - Match permissions to job function
3. **Regular reviews** - Audit and update permissions quarterly
4. **Revoke unused access** - Remove permissions for inactive users

This comprehensive system ensures secure, auditable user registration while providing app owners complete control over their platform's growth and security.
