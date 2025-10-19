from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser
import uuid

class SuperOwner(models.Model):
    """Special model to identify app owners/super administrators"""
    DELEGATION_LEVELS = [
        ('full', 'Full Admin Access'),
        ('company_management', 'Company Management Only'),
        ('user_management', 'User Management Only'),
        ('billing_management', 'Billing Management Only'),
        ('read_only', 'Read-Only Access'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='super_owner_profile')
    is_primary_owner = models.BooleanField(default=False, help_text="Primary app owner - cannot be revoked")
    delegation_level = models.CharField(max_length=30, choices=DELEGATION_LEVELS, default='read_only')
    can_manage_companies = models.BooleanField(default=False)
    can_manage_users = models.BooleanField(default=False)
    can_activate_accounts = models.BooleanField(default=False)
    can_access_django_admin = models.BooleanField(default=False)
    can_delegate_permissions = models.BooleanField(default=False)
    can_manage_billing = models.BooleanField(default=False)
    can_view_system_analytics = models.BooleanField(default=False)
    
    # Restrictions
    allowed_companies = models.ManyToManyField('Company', blank=True, help_text="If empty, can manage all companies")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_super_owners')
    
    class Meta:
        verbose_name = 'Super Owner'
        verbose_name_plural = 'Super Owners'
        ordering = ['-is_primary_owner', 'user__first_name', 'user__last_name']
    
    def __str__(self):
        status = "Primary Owner" if self.is_primary_owner else f"Super Admin ({self.get_delegation_level_display()})"
        return f"{self.user.get_full_name() or self.user.username} - {status}"
    
    def save(self, *args, **kwargs):
        # Ensure only one primary owner exists
        if self.is_primary_owner:
            SuperOwner.objects.filter(is_primary_owner=True).exclude(pk=self.pk).update(is_primary_owner=False)
        
        # Primary owner gets all permissions
        if self.is_primary_owner:
            self.delegation_level = 'full'
            self.can_manage_companies = True
            self.can_manage_users = True
            self.can_activate_accounts = True
            self.can_access_django_admin = True
            self.can_delegate_permissions = True
            self.can_manage_billing = True
            self.can_view_system_analytics = True
        
        super().save(*args, **kwargs)
    
    def can_manage_company(self, company):
        """Check if super owner can manage a specific company"""
        if not self.can_manage_companies:
            return False
        if self.allowed_companies.exists():
            return self.allowed_companies.filter(id=company.id).exists()
        return True
    
    def get_manageable_companies(self):
        """Get companies this super owner can manage"""
        if not self.can_manage_companies:
            return Company.objects.none()
        if self.allowed_companies.exists():
            return self.allowed_companies.all()
        return Company.objects.all()

class AccountActivationRequest(models.Model):
    """Model to handle account activation requests with document upload support"""
    REQUEST_TYPES = [
        ('company_registration', 'Company Registration'),
        ('individual_registration', 'Individual Registration'),
        ('user_invitation', 'User Invitation'),
        ('user_registration', 'User Registration'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('documents_required', 'Documents Required'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request_type = models.CharField(max_length=30, choices=REQUEST_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Requester information
    email = models.EmailField()
    username = models.CharField(max_length=150, blank=True)  # For login flexibility
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    
    # Company information (for company registration)
    company_name = models.CharField(max_length=200, blank=True)
    company_description = models.TextField(blank=True)
    company_website = models.URLField(blank=True)
    company_address = models.TextField(blank=True)
    company_registration_number = models.CharField(max_length=100, blank=True)
    
    # User information (for user invitations)
    target_company = models.ForeignKey('Company', on_delete=models.CASCADE, null=True, blank=True)
    requested_role = models.CharField(max_length=100, blank=True)
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_activation_requests')
    
    # Approval information
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_activation_requests')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # System fields
    activation_token = models.CharField(max_length=100, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Additional data
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['email', 'status']),
            models.Index(fields=['activation_token']),
        ]
    
    def __str__(self):
        return f"{self.get_request_type_display()} - {self.email} ({self.get_status_display()})"
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def approve(self, approved_by_user):
        """Approve the activation request"""
        if self.status != 'pending':
            raise ValidationError("Only pending requests can be approved")
        
        if self.is_expired:
            self.status = 'expired'
            self.save()
            raise ValidationError("Request has expired")
        
        self.status = 'approved'
        self.approved_by = approved_by_user
        self.approved_at = timezone.now()
        self.save()
    
    def reject(self, rejected_by_user, reason=""):
        """Reject the activation request"""
        if self.status not in ['pending', 'under_review', 'documents_required']:
            raise ValidationError("Only pending or under review requests can be rejected")
        
        self.status = 'rejected'
        self.approved_by = rejected_by_user
        self.approved_at = timezone.now()
        self.rejection_reason = reason
        self.save()
    
    def mark_under_review(self, reviewer_user):
        """Mark request as under review"""
        if self.status != 'pending':
            raise ValidationError("Only pending requests can be marked under review")
        
        self.status = 'under_review'
        self.approved_by = reviewer_user
        self.save()
    
    def require_documents(self, reviewer_user, reason=""):
        """Request additional documents"""
        if self.status not in ['pending', 'under_review']:
            raise ValidationError("Only pending or under review requests can require documents")
        
        self.status = 'documents_required'
        self.approved_by = reviewer_user
        self.rejection_reason = reason
        self.save()

class TimeStampedModel(models.Model):
    """Abstract base model with timestamp fields"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

class DocumentUpload(TimeStampedModel):
    """Model to handle document uploads for registration requests"""
    DOCUMENT_TYPES = [
        ('business_registration', 'Business Registration Certificate'),
        ('tax_certificate', 'Tax Registration Certificate'),
        ('cac_certificate', 'CAC Certificate'),
        ('director_id', 'Director ID Document'),
        ('utility_bill', 'Utility Bill'),
        ('bank_statement', 'Bank Statement'),
        ('individual_id', 'Individual ID Document'),
        ('passport', 'Passport'),
        ('license', 'Professional License'),
        ('other', 'Other Document'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('requires_revision', 'Requires Revision'),
    ]
    
    activation_request = models.ForeignKey(
        AccountActivationRequest, 
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='registration_documents/', max_length=500)
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="Size in bytes")
    description = models.TextField(blank=True)
    
    # Review status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='reviewed_documents'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['activation_request', 'document_type']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.activation_request.email}"
    
    def approve(self, reviewer_user, notes=""):
        """Approve the document"""
        self.status = 'approved'
        self.reviewed_by = reviewer_user
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()
    
    def reject(self, reviewer_user, notes=""):
        """Reject the document"""
        self.status = 'rejected'
        self.reviewed_by = reviewer_user
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()
    
    def require_revision(self, reviewer_user, notes=""):
        """Mark document as requiring revision"""
        self.status = 'requires_revision'
        self.reviewed_by = reviewer_user
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()
    
    @property
    def is_image(self):
        """Check if uploaded file is an image"""
        return self.file.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg'))
    
    @property
    def is_pdf(self):
        """Check if uploaded file is a PDF"""
        return self.file.name.lower().endswith('.pdf')
    
    @property
    def file_size_mb(self):
        """Get file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)

class Company(TimeStampedModel):
    """Multi-tenant company model"""
    SUBSCRIPTION_CHOICES = [
        ('trial', 'Trial'),
        ('basic', 'Basic'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    
    # Contact Information
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    website = models.URLField(blank=True)
    registration_number = models.CharField(max_length=100, blank=True, help_text='Company registration number')
    
    # Subscription & Billing
    subscription_type = models.CharField(max_length=20, choices=SUBSCRIPTION_CHOICES, default='trial')
    subscription_start_date = models.DateTimeField(auto_now_add=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Settings
    timezone = models.CharField(max_length=50, default='UTC')
    currency = models.CharField(max_length=3, default='USD')
    
    class Meta:
        verbose_name_plural = 'Companies'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def is_subscription_active(self):
        """Check if subscription is currently active"""
        if not self.is_active:
            return False
        if self.subscription_end_date:
            return timezone.now() <= self.subscription_end_date
        return True
    
    def get_owner(self):
        """Get the company owner (admin user)"""
        try:
            admin_membership = self.memberships.filter(
                role__is_admin=True,
                status='active'
            ).select_related('user').first()
            return admin_membership.user if admin_membership else None
        except:
            return None
    
    @property
    def owner(self):
        """Property to get company owner"""
        return self.get_owner()

class Role(TimeStampedModel):
    """Role model for RBAC"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='roles')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_admin = models.BooleanField(default=False)
    is_supervisor = models.BooleanField(default=False)  # For MD/CEO level access
    is_team_member = models.BooleanField(default=False)  # For team member access
    
    class Meta:
        unique_together = ['company', 'name']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.company.name} - {self.name}"

class Permission(models.Model):
    """Granular permissions for different features"""
    RESOURCE_CHOICES = [
        ('projects', 'Projects'),
        ('expenses', 'Expenses'),
        ('contractors', 'Contractors'),
        ('reports', 'Reports'),
        ('users', 'User Management'),
        ('company', 'Company Settings'),
        ('billing', 'Billing & Subscriptions'),
    ]
    
    ACTION_CHOICES = [
        ('view', 'View'),
        ('create', 'Create'),
        ('edit', 'Edit'),
        ('delete', 'Delete'),
        ('approve', 'Approve'),
        ('export', 'Export'),
    ]
    
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='permissions')
    resource = models.CharField(max_length=50, choices=RESOURCE_CHOICES)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    
    class Meta:
        unique_together = ['role', 'resource', 'action']
    
    def __str__(self):
        return f"{self.role.name} - {self.action} {self.resource}"

class CompanyMembership(TimeStampedModel):
    """Link users to companies with roles"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('invited', 'Invited'),
        ('suspended', 'Suspended'),
        ('left', 'Left'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='company_memberships')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='memberships')
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='invitations_sent')
    invitation_token = models.CharField(max_length=100, blank=True)
    joined_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'company']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} @ {self.company.name} ({self.role.name if self.role else 'No Role'})"
    
    def has_permission(self, resource, action):
        """Check if user has specific permission"""
        if not self.role:
            return False
        return self.role.permissions.filter(resource=resource, action=action).exists()
    
    def is_company_admin(self):
        """Check if user is company admin"""
        return self.role and self.role.is_admin
    
    def is_company_supervisor(self):
        """Check if user is company supervisor (MD/CEO)"""
        return self.role and self.role.is_supervisor
    
    def is_team_member(self):
        """Check if user is team member"""
        return self.role and self.role.is_team_member

class UserProfile(models.Model):
    """Extended user profile with enhanced features"""
    ACCOUNT_TYPES = [
        ('company', 'Company Account'),
        ('individual', 'Individual Account'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    notification_preferences = models.JSONField(default=dict, blank=True)
    last_company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Account type and verification
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='individual')
    is_verified = models.BooleanField(default=False, help_text="Email verified")
    verification_token = models.CharField(max_length=100, blank=True)
    
    # Document verification
    documents_submitted = models.BooleanField(default=False)
    documents_verified = models.BooleanField(default=False)
    verification_notes = models.TextField(blank=True)
    
    # Account activation fields
    is_account_active = models.BooleanField(default=False, help_text="Account activated by SuperOwner")
    activation_requested_at = models.DateTimeField(null=True, blank=True)
    activated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='activated_users')
    activated_at = models.DateTimeField(null=True, blank=True)
    
    # Additional profile fields
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} Profile"
    
    def get_active_memberships(self):
        """Get all active company memberships"""
        return self.user.company_memberships.filter(status='active')
    
    def get_companies(self):
        """Get all companies user belongs to"""
        return Company.objects.filter(
            memberships__user=self.user,
            memberships__status='active'
        ).distinct()
    
    def is_super_owner(self):
        """Check if user is a super owner"""
        return hasattr(self.user, 'super_owner_profile')
    
    def is_primary_super_owner(self):
        """Check if user is the primary super owner"""
        return self.is_super_owner() and self.user.super_owner_profile.is_primary_owner
    
    def get_super_owner_permissions(self):
        """Get super owner permissions if user is super owner"""
        if self.is_super_owner():
            return self.user.super_owner_profile
        return None
    
    def can_access_django_admin(self):
        """Check if user can access Django admin"""
        if self.is_super_owner():
            return self.user.super_owner_profile.can_access_django_admin
        return False
    
    def can_activate_accounts(self):
        """Check if user can activate accounts"""
        if self.is_super_owner():
            return self.user.super_owner_profile.can_activate_accounts
        return False
    
    def can_manage_all_companies(self):
        """Check if user can manage all companies"""
        if self.is_super_owner():
            super_owner = self.user.super_owner_profile
            return super_owner.can_manage_companies and not super_owner.allowed_companies.exists()
        return False

class NotificationTemplate(TimeStampedModel):
    """Master template for all available notification types"""
    NOTIFICATION_TYPES = [
        ('expense_created', 'Expense Created'),
        ('expense_updated', 'Expense Updated'),
        ('expense_approved', 'Expense Approved'),
        ('expense_rejected', 'Expense Rejected'),
        ('expense_overbudget', 'Expense Over Budget'),
        ('project_created', 'Project Created'),
        ('project_updated', 'Project Updated'),
        ('project_milestone', 'Project Milestone Reached'),
        ('project_overdue', 'Project Overdue'),
        ('project_completed', 'Project Completed'),
        ('budget_warning', 'Budget Warning (75%)'),
        ('budget_critical', 'Budget Critical (90%)'),
        ('contractor_assigned', 'Contractor Assigned'),
        ('contractor_removed', 'Contractor Removed'),
        ('user_invited', 'User Invited'),
        ('user_joined', 'User Joined Company'),
        ('role_changed', 'Role Changed'),
        ('system_update', 'System Update'),
        ('system_maintenance', 'System Maintenance'),
        ('security_alert', 'Security Alert'),
        ('report_ready', 'Report Ready'),
        ('backup_completed', 'Backup Completed'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    CONTROL_LEVEL_CHOICES = [
        ('admin_only', 'Admin Only - Users cannot disable'),
        ('admin_default', 'Admin Default - Users can override'),
        ('user_choice', 'User Choice - Users control entirely'),
        ('role_based', 'Role Based - Depends on user role'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='notification_templates')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    name = models.CharField(max_length=200)
    description = models.TextField()
    default_priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    control_level = models.CharField(max_length=20, choices=CONTROL_LEVEL_CHOICES, default='user_choice')
    
    # Default delivery methods
    default_in_app = models.BooleanField(default=True)
    default_email = models.BooleanField(default=True)
    default_sms = models.BooleanField(default=False)
    
    # Role-based access
    allowed_roles = models.ManyToManyField(Role, blank=True, help_text="Roles that can receive this notification")
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['company', 'notification_type']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.company.name} - {self.name}"

class UserNotificationPreference(TimeStampedModel):
    """Individual user's notification preferences"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_preferences')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='user_notification_preferences')
    notification_template = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE, related_name='user_preferences')
    
    # User's chosen delivery methods
    in_app_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    
    # User can't disable if admin_only
    is_enabled = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['user', 'company', 'notification_template']
        ordering = ['notification_template__name']
    
    def __str__(self):
        return f"{self.user.username} - {self.notification_template.name}"
    
    def can_user_modify(self):
        """Check if user can modify this preference"""
        template = self.notification_template
        if template.control_level == 'admin_only':
            return False
        elif template.control_level == 'role_based':
            # Check if user's role is allowed
            try:
                membership = CompanyMembership.objects.get(user=self.user, company=self.company)
                return template.allowed_roles.filter(id=membership.role.id).exists()
            except CompanyMembership.DoesNotExist:
                return False
        return True

class Notification(TimeStampedModel):
    """Actual notifications sent to users"""
    DELIVERY_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='notifications')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications')
    notification_template = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE, related_name='notifications', null=True)
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    priority = models.CharField(max_length=20, choices=NotificationTemplate.PRIORITY_CHOICES, default='medium')
    
    # Delivery tracking
    in_app_status = models.CharField(max_length=20, choices=DELIVERY_STATUS_CHOICES, default='pending')
    email_status = models.CharField(max_length=20, choices=DELIVERY_STATUS_CHOICES, default='pending')
    sms_status = models.CharField(max_length=20, choices=DELIVERY_STATUS_CHOICES, default='pending')
    
    # Delivery timestamps
    in_app_sent_at = models.DateTimeField(null=True, blank=True)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    sms_sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Additional data (JSON for flexibility)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Related objects (optional)
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'read_at']),
            models.Index(fields=['company', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"
    
    @property
    def is_read(self):
        return self.read_at is not None
    
    @property
    def notification_type(self):
        return self.notification_template.notification_type
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.read_at:
            self.read_at = timezone.now()
            self.in_app_status = 'read'
            self.save()
    
    def should_send_email(self):
        """Check if email should be sent based on user preferences"""
        try:
            pref = UserNotificationPreference.objects.get(
                user=self.recipient,
                company=self.company,
                notification_template=self.notification_template
            )
            return pref.email_enabled and pref.is_enabled
        except UserNotificationPreference.DoesNotExist:
            return self.notification_template.default_email
    
    def should_send_sms(self):
        """Check if SMS should be sent based on user preferences"""
        try:
            pref = UserNotificationPreference.objects.get(
                user=self.recipient,
                company=self.company,
                notification_template=self.notification_template
            )
            return pref.sms_enabled and pref.is_enabled
        except UserNotificationPreference.DoesNotExist:
            return self.notification_template.default_sms


