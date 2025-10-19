"""
Enhanced registration request workflow with comprehensive notifications and status management
"""

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.models import User
from django.utils.text import slugify
import secrets

from .models import (
    AccountActivationRequest, Company, Role, Permission, 
    CompanyMembership, UserProfile, SuperOwner
)


class RegistrationRequestHandler:
    """Handle registration requests with comprehensive workflow"""
    
    def __init__(self, request):
        self.request = request
        
    def create_company_registration(self, form_data, documents=None):
        """Create a company registration request"""
        with transaction.atomic():
            # Create activation request
            activation_request = AccountActivationRequest.objects.create(
                request_type='company_registration',
                status='pending',
                email=form_data['admin_email'],
                username=form_data.get('admin_username') or form_data['admin_email'],
                first_name=form_data['admin_first_name'],
                last_name=form_data['admin_last_name'],
                phone=form_data.get('admin_phone', ''),
                company_name=form_data['company_name'],
                company_description=form_data.get('company_description', ''),
                company_website=form_data.get('company_website', ''),
                company_address=form_data.get('company_address', ''),
                company_registration_number=form_data.get('company_registration_number', ''),
                activation_token=secrets.token_urlsafe(32),
                expires_at=timezone.now() + timezone.timedelta(days=30),
                metadata={
                    'request_source': 'web_form',
                    'ip_address': self.request.META.get('REMOTE_ADDR', ''),
                    'user_agent': self.request.META.get('HTTP_USER_AGENT', '')[:200],
                }
            )
            
            # Send notification to applicant
            self.send_request_submitted_notification(activation_request)
            
            # Notify super owners
            self.notify_super_owners_new_request(activation_request)
            
            return activation_request
    
    def create_individual_registration(self, form_data, documents=None):
        """Create an individual registration request"""
        with transaction.atomic():
            activation_request = AccountActivationRequest.objects.create(
                request_type='individual_registration',
                status='pending',
                email=form_data['email'],
                username=form_data.get('username') or form_data['email'],
                first_name=form_data['first_name'],
                last_name=form_data['last_name'],
                phone=form_data.get('phone', ''),
                activation_token=secrets.token_urlsafe(32),
                expires_at=timezone.now() + timezone.timedelta(days=30),
                metadata={
                    'address': form_data.get('address', ''),
                    'date_of_birth': form_data.get('date_of_birth').isoformat() if form_data.get('date_of_birth') else None,
                    'request_source': 'web_form',
                    'ip_address': self.request.META.get('REMOTE_ADDR', ''),
                    'user_agent': self.request.META.get('HTTP_USER_AGENT', '')[:200],
                }
            )
            
            # Send notification to applicant
            self.send_request_submitted_notification(activation_request)
            
            # Notify super owners
            self.notify_super_owners_new_request(activation_request)
            
            return activation_request
    
    def approve_request(self, activation_request, approved_by):
        """Approve a registration request and create accounts"""
        with transaction.atomic():
            # Update request status
            activation_request.status = 'approved'
            activation_request.approved_by = approved_by
            activation_request.approved_at = timezone.now()
            activation_request.save()
            
            user = None
            
            if activation_request.request_type == 'company_registration':
                user = self._create_company_and_admin(activation_request)
            elif activation_request.request_type == 'individual_registration':
                user = self._create_individual_user(activation_request)
            
            # Send approval notification
            self.send_approval_notification(activation_request, user)
            
            return user
    
    def reject_request(self, activation_request, rejected_by, reason=''):
        """Reject a registration request"""
        with transaction.atomic():
            activation_request.status = 'rejected'
            activation_request.approved_by = rejected_by
            activation_request.approved_at = timezone.now()
            activation_request.rejection_reason = reason
            activation_request.save()
            
            # Send rejection notification
            self.send_rejection_notification(activation_request, reason)
    
    def request_additional_documents(self, activation_request, reviewed_by, message=''):
        """Request additional documents from applicant"""
        with transaction.atomic():
            activation_request.status = 'documents_required'
            activation_request.approved_by = reviewed_by
            activation_request.rejection_reason = message
            activation_request.save()
            
            # Send document request notification
            self.send_document_request_notification(activation_request, message)
    
    def _create_company_and_admin(self, activation_request):
        """Create company and admin user"""
        # Create admin user
        user = User.objects.create_user(
            username=activation_request.username,
            email=activation_request.email,
            first_name=activation_request.first_name,
            last_name=activation_request.last_name,
        )
        
        # Generate temporary password and send via email
        import secrets
        import string
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        user.set_password(temp_password)
        user.save()
        
        # Create user profile
        profile = UserProfile.objects.create(
            user=user,
            phone=activation_request.phone,
            is_account_active=True,
            account_type='company_admin',
            activated_by=activation_request.approved_by,
            activated_at=timezone.now(),
            is_verified=True
        )
        
        # Create company
        company = Company.objects.create(
            name=activation_request.company_name,
            slug=slugify(activation_request.company_name),
            description=activation_request.company_description,
            email=activation_request.email,
            website=activation_request.company_website,
            address=activation_request.company_address,
            is_active=True
        )
        
        profile.last_company = company
        profile.save()
        
        # Create default roles and permissions
        self._create_company_default_roles(company, user)
        
        # Send login credentials
        self.send_login_credentials(user, temp_password, company)
        
        return user
    
    def _create_individual_user(self, activation_request):
        """Create individual user account"""
        # Create user
        user = User.objects.create_user(
            username=activation_request.username,
            email=activation_request.email,
            first_name=activation_request.first_name,
            last_name=activation_request.last_name,
        )
        
        # Generate temporary password
        import secrets
        import string
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        user.set_password(temp_password)
        user.save()
        
        # Create user profile
        profile = UserProfile.objects.create(
            user=user,
            phone=activation_request.phone,
            is_account_active=True,
            account_type='individual',
            activated_by=activation_request.approved_by,
            activated_at=timezone.now(),
            is_verified=True
        )
        
        # Send login credentials
        self.send_login_credentials(user, temp_password)
        
        return user
    
    def _create_company_default_roles(self, company, admin_user):
        """Create default roles for a new company"""
        # Create admin role
        admin_role = Role.objects.create(
            company=company,
            name='Company Admin',
            description='Full company administration access',
            is_admin=True,
            is_supervisor=False
        )
        
        # Create supervisor role
        supervisor_role = Role.objects.create(
            company=company,
            name='Supervisor',
            description='High-level oversight and reporting access',
            is_admin=False,
            is_supervisor=True
        )
        
        # Create employee role
        employee_role = Role.objects.create(
            company=company,
            name='Employee',
            description='Basic employee access',
            is_admin=False,
            is_supervisor=False
        )
        
        # Add permissions to admin role
        admin_permissions = []
        for resource, _ in Permission.RESOURCE_CHOICES:
            for action, _ in Permission.ACTION_CHOICES:
                admin_permissions.append(
                    Permission(role=admin_role, resource=resource, action=action)
                )
        Permission.objects.bulk_create(admin_permissions)
        
        # Add basic permissions to other roles
        self._add_basic_permissions(supervisor_role, employee_role)
        
        # Create membership for admin user
        CompanyMembership.objects.create(
            user=admin_user,
            company=company,
            role=admin_role,
            status='active',
            joined_date=timezone.now()
        )
    
    def _add_basic_permissions(self, supervisor_role, employee_role):
        """Add basic permissions to supervisor and employee roles"""
        # Supervisor permissions
        supervisor_permissions = []
        supervisor_actions = ['view', 'export']
        for resource, _ in Permission.RESOURCE_CHOICES:
            for action in supervisor_actions:
                supervisor_permissions.append(
                    Permission(role=supervisor_role, resource=resource, action=action)
                )
        Permission.objects.bulk_create(supervisor_permissions)
        
        # Employee permissions
        employee_permissions = []
        employee_resources = ['projects', 'expenses', 'contractors']
        employee_actions = ['view', 'create', 'edit']
        for resource in employee_resources:
            for action in employee_actions:
                employee_permissions.append(
                    Permission(role=employee_role, resource=resource, action=action)
                )
        Permission.objects.bulk_create(employee_permissions)
    
    # Email notifications
    def send_request_submitted_notification(self, activation_request):
        """Send notification when request is submitted"""
        subject = 'Registration Request Submitted - Construction Tracker'
        context = {
            'activation_request': activation_request,
            'site_url': settings.SITE_URL,
            'status_url': f"{settings.SITE_URL}/registration/status/{activation_request.activation_token}/"
        }
        
        html_message = render_to_string('core/emails/request_submitted.html', context)
        plain_message = render_to_string('core/emails/request_submitted.txt', context)
        
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[activation_request.email],
            fail_silently=True,
        )
    
    def send_approval_notification(self, activation_request, user):
        """Send notification when request is approved"""
        subject = 'Account Approved - Construction Tracker'
        context = {
            'activation_request': activation_request,
            'user': user,
            'site_url': settings.SITE_URL,
            'login_url': f"{settings.SITE_URL}/login/"
        }
        
        html_message = render_to_string('core/emails/request_approved.html', context)
        plain_message = render_to_string('core/emails/request_approved.txt', context)
        
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[activation_request.email],
            fail_silently=True,
        )
    
    def send_rejection_notification(self, activation_request, reason):
        """Send notification when request is rejected"""
        subject = 'Registration Request Update - Construction Tracker'
        context = {
            'activation_request': activation_request,
            'rejection_reason': reason,
            'site_url': settings.SITE_URL,
            'contact_email': settings.DEFAULT_FROM_EMAIL
        }
        
        html_message = render_to_string('core/emails/request_rejected.html', context)
        plain_message = render_to_string('core/emails/request_rejected.txt', context)
        
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[activation_request.email],
            fail_silently=True,
        )
    
    def send_document_request_notification(self, activation_request, message):
        """Send notification when additional documents are requested"""
        subject = 'Additional Documents Required - Construction Tracker'
        context = {
            'activation_request': activation_request,
            'message': message,
            'site_url': settings.SITE_URL,
            'status_url': f"{settings.SITE_URL}/registration/status/{activation_request.activation_token}/"
        }
        
        html_message = render_to_string('core/emails/documents_required.html', context)
        plain_message = render_to_string('core/emails/documents_required.txt', context)
        
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[activation_request.email],
            fail_silently=True,
        )
    
    def send_login_credentials(self, user, password, company=None):
        """Send login credentials to new user"""
        subject = 'Your Login Credentials - Construction Tracker'
        context = {
            'user': user,
            'username': user.username,
            'password': password,
            'company': company,
            'site_url': settings.SITE_URL,
            'login_url': f"{settings.SITE_URL}/login/"
        }
        
        html_message = render_to_string('core/emails/login_credentials.html', context)
        plain_message = render_to_string('core/emails/login_credentials.txt', context)
        
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    
    def notify_super_owners_new_request(self, activation_request):
        """Notify all super owners about new registration request"""
        super_owners = SuperOwner.objects.filter(
            can_activate_accounts=True
        ).select_related('user')
        
        if not super_owners.exists():
            return
        
        recipient_emails = [so.user.email for so in super_owners]
        
        subject = f'New Registration Request - {activation_request.get_request_type_display()}'
        context = {
            'activation_request': activation_request,
            'site_url': settings.SITE_URL,
            'admin_url': f"{settings.SITE_URL}/super-owner/"
        }
        
        html_message = render_to_string('core/emails/super_owner_notification.html', context)
        plain_message = render_to_string('core/emails/super_owner_notification.txt', context)
        
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_emails,
            fail_silently=True,
        )
