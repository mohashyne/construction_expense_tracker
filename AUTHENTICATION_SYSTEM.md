# Enhanced Authentication System with Document Upload and Approval Workflow

This document describes the comprehensive authentication system implemented for the Construction Expense Tracker application.

## Overview

The system supports:
1. **Company Registration** - Companies can register with document upload and require approval
2. **Individual Registration** - Individuals can register with document verification
3. **Email/Username Login** - Flexible login options
4. **Hierarchical User Management** - Company owners can add staff after approval
5. **Document-Based Approval Workflow** - Super owners review and approve registrations

## Registration Types

### 1. Company Registration (`/register/company/`)

Companies must submit:

**Required Information:**
- Company name, description, address
- Company registration number
- Contact person details (name, email, phone)
- Optional username (defaults to email)

**Required Documents:**
- Business Registration Certificate
- Director/Owner ID Document

**Optional Documents:**
- Tax Registration Certificate
- CAC Certificate  
- Utility Bill (address proof)

**Process:**
1. Company submits registration form with documents
2. Super owners receive email notification
3. Super owners review documents and approve/reject
4. Upon approval:
   - Company account is created
   - Admin user is created with generated password
   - Default roles are set up
   - Welcome email sent with login credentials

### 2. Individual Registration (`/register/individual/`)

Individuals must submit:

**Required Information:**
- Personal details (name, email, phone)
- Optional username (defaults to email)
- Address, date of birth (optional)

**Required Documents:**
- Government-issued ID Document

**Optional Documents:**
- Passport
- Professional License

**Process:**
1. Individual submits registration form with documents
2. Super owners review and approve/reject
3. Upon approval:
   - User account is created
   - Welcome email sent with login credentials

## Authentication Features

### Flexible Login System
- Users can login with **email OR username**
- Enhanced `FlexibleAuthenticationForm` automatically detects email vs username
- Account activation check during login

### Account Activation
- All new accounts require super owner approval
- Users with pending accounts cannot login
- Activation status checked during authentication

## User Management Hierarchy

### Super Owners
- Can review and approve/reject registration requests
- Can view all uploaded documents
- Can manage system-wide settings
- Access admin panel at `/admin/activation-requests/`

### Company Owners/Admins
- Can invite users to their company ONLY after their company is approved
- Can manage roles and permissions within their company
- Can add staff members who get auto-approved access

### Staff/Users
- Added by company owners
- Get immediate access (no separate approval needed)
- Inherit permissions from assigned roles

## Document Management

### Supported File Types
- PDF, JPG, JPEG, PNG
- Maximum 10MB per file

### Document Types
**Company Documents:**
- `business_registration` - Business Registration Certificate
- `tax_certificate` - Tax Registration Certificate
- `cac_certificate` - CAC Certificate
- `director_id` - Director ID Document
- `utility_bill` - Utility Bill

**Individual Documents:**
- `individual_id` - Government ID Document
- `passport` - Passport
- `license` - Professional License

### Document Review Process
1. Documents uploaded during registration
2. Super owners can review each document individually
3. Documents can be: Approved, Rejected, or marked for Revision
4. Overall registration status depends on document review

## Registration Status Workflow

### Status Types
- `pending` - Initial submission, awaiting review
- `under_review` - Being actively reviewed by super owner
- `documents_required` - Additional documents needed
- `approved` - Registration approved, accounts created
- `rejected` - Registration rejected
- `expired` - Registration expired (30 days)

### Status Tracking
Users can check status at: `/registration/status/{token}/`
- Shows overall status
- Lists all uploaded documents with individual status
- Provides next steps based on current status

## Email Notifications

### Registration Submitted
- Sent to super owners when new registration submitted
- Includes basic information and link to admin panel

### Status Updates
- Approval: Welcome email with login credentials
- Rejection: Email with reason for rejection
- Documents Required: Email requesting additional documents

### User Invitations
- Existing users: Invitation to join company
- New users: Welcome email with generated credentials

## API Endpoints

### Public (No Authentication Required)
- `POST /register/company/` - Company registration
- `POST /register/individual/` - Individual registration
- `GET /registration/status/{token}/` - Check status
- `POST /login/` - User authentication

### Super Owner Only
- `GET /admin/activation-requests/` - List all requests
- `GET /admin/activation-requests/{id}/` - Request details
- `POST /admin/activation-requests/{id}/` - Approve/reject
- `GET /admin/documents/{id}/download/` - Download document

### Company Admin/Supervisor Only
- `POST /users/invite/` - Invite users (enhanced)
- Company management endpoints (existing)

## Database Models

### Enhanced Models

**AccountActivationRequest**
- Stores registration requests with status tracking
- Links to uploaded documents
- Tracks approval workflow

**DocumentUpload** 
- Stores uploaded documents with metadata
- Individual review status per document
- Secure file storage with access control

**UserProfile** (Enhanced)
- Account type (company/individual)
- Document verification status
- Enhanced activation tracking

## Security Features

### Document Access Control
- Only super owners can view uploaded documents
- Secure document serving with permission checks
- Protected file paths

### Account Verification
- Multi-step verification process
- Document-based validation
- Email verification tokens

### Password Security
- Generated passwords for new accounts
- Force password change recommendations
- Secure password reset (existing system)

## Configuration

### Environment Variables
```bash
# Add to .env file
SITE_URL=https://yourdomain.com  # Used in email links
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

### Media Settings
Ensure proper media handling for document uploads:
```python
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

## Usage Examples

### Creating Super Owner
```python
from django.contrib.auth.models import User
from core.models import SuperOwner, UserProfile

# Create super owner user
user = User.objects.create_user('superowner', 'admin@company.com', 'password')
profile = UserProfile.objects.create(user=user, is_account_active=True)

# Create super owner profile
SuperOwner.objects.create(
    user=user,
    is_primary_owner=True,
    can_activate_accounts=True,
    can_manage_companies=True,
    can_manage_users=True
)
```

### Checking Registration Status
```python
from core.models import AccountActivationRequest

# Get registration by token
request = AccountActivationRequest.objects.get(activation_token='token-here')
print(f"Status: {request.get_status_display()}")
print(f"Documents: {request.documents.count()}")
```

## Migration Guide

### From Existing System
1. Run migrations: `python manage.py migrate`
2. Create super owner accounts (see above)
3. Update templates to use new registration endpoints
4. Configure email settings for notifications

### Template Updates
Update registration links:
```html
<!-- Old -->
<a href="{% url 'core:register' %}">Register</a>

<!-- New -->
<a href="{% url 'core:company_registration_request' %}">Register Company</a>
<a href="{% url 'core:individual_registration_request' %}">Register Individual</a>
```

## Testing

### Test Company Registration
1. Visit `/register/company/`
2. Fill form and upload documents
3. Check email notifications
4. Login as super owner
5. Review at `/admin/activation-requests/`
6. Approve request
7. Check approval email
8. Test login with generated credentials

### Test User Invitation
1. Login as approved company owner
2. Go to company management
3. Invite new user
4. Check invitation email
5. Test login with new user

## Troubleshooting

### Common Issues

**Documents not uploading**
- Check file size (max 10MB)
- Verify file format (PDF, JPG, PNG)
- Check media settings

**Email notifications not sending**
- Verify email backend configuration
- Check SITE_URL setting
- Test email connectivity

**Permission denied errors**
- Verify user has proper super owner status
- Check account activation status
- Ensure proper role assignments

**Login failures**
- Check account activation status
- Verify email/username flexibility
- Test password reset flow

This enhanced authentication system provides a robust, document-based approval workflow while maintaining the existing functionality for approved users.
