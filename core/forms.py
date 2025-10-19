from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import secrets
import uuid
from .models import Company, Role, Permission, CompanyMembership, UserProfile, AccountActivationRequest, DocumentUpload

class CompanyRegistrationForm(forms.ModelForm):
    """Form for company registration during SaaS onboarding"""
    admin_first_name = forms.CharField(max_length=30, help_text='Admin contact person first name')
    admin_last_name = forms.CharField(max_length=30, help_text='Admin contact person last name')
    admin_email = forms.EmailField(help_text='Admin contact person email (used for login)')
    admin_password = forms.CharField(widget=forms.PasswordInput, help_text='Password for admin account')
    admin_password_confirm = forms.CharField(widget=forms.PasswordInput, help_text='Confirm password')
    admin_phone = forms.CharField(max_length=20, required=False, help_text='Admin contact phone')
    
    terms_accepted = forms.BooleanField(
        required=True, 
        help_text='I agree to the Terms of Service and Privacy Policy'
    )
    
    class Meta:
        model = Company
        fields = ['name', 'description', 'email', 'phone', 'address', 'website', 'timezone', 'currency']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'address': forms.Textarea(attrs={'rows': 2}),
            'timezone': forms.Select(choices=[
                ('UTC', 'UTC'),
                ('US/Eastern', 'Eastern Time'),
                ('US/Central', 'Central Time'),
                ('US/Mountain', 'Mountain Time'),
                ('US/Pacific', 'Pacific Time'),
                ('Europe/London', 'London'),
                ('Europe/Paris', 'Paris'),
                ('Asia/Tokyo', 'Tokyo'),
            ]),
            'currency': forms.Select(choices=[
                ('USD', 'US Dollar'),
                ('EUR', 'Euro'),
                ('GBP', 'British Pound'),
                ('CAD', 'Canadian Dollar'),
                ('AUD', 'Australian Dollar'),
            ]),
        }
    
    def clean_admin_email(self):
        email = self.cleaned_data['admin_email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email
    
    def clean_admin_password_confirm(self):
        password = self.cleaned_data.get('admin_password')
        password_confirm = self.cleaned_data.get('admin_password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Passwords do not match.')
        return password_confirm
    
    def clean_name(self):
        name = self.cleaned_data['name']
        slug = slugify(name)
        if Company.objects.filter(slug=slug).exists():
            raise forms.ValidationError('A company with this name already exists.')
        return name
    
    def save(self, commit=True):
        company = super().save(commit=False)
        company.slug = slugify(company.name)
        
        if commit:
            company.save()
            
            # Create admin user
            admin_user = User.objects.create_user(
                username=self.cleaned_data['admin_email'],
                email=self.cleaned_data['admin_email'],
                first_name=self.cleaned_data['admin_first_name'],
                last_name=self.cleaned_data['admin_last_name'],
                password=self.cleaned_data['admin_password']
            )
            
            # Create or update user profile
            profile, created = UserProfile.objects.get_or_create(
                user=admin_user,
                defaults={
                    'phone': self.cleaned_data.get('admin_phone', ''),
                    'last_company': company
                }
            )
            if not created:
                # Update existing profile
                profile.phone = self.cleaned_data.get('admin_phone', '') or profile.phone
                profile.last_company = company
                profile.save()
            
            # Create default roles and permissions
            self._create_default_roles(company, admin_user)
            
        return company
    
    def _create_default_roles(self, company, admin_user):
        """Create default roles with appropriate permissions"""
        # Create default admin role
        admin_role = Role.objects.create(
            company=company,
            name='Company Admin',
            description='Full access to all company features and settings',
            is_admin=True,
            is_supervisor=False
        )
        
        # Create default supervisor role
        supervisor_role = Role.objects.create(
            company=company,
            name='Supervisor/Executive',
            description='High-level oversight and reporting access',
            is_admin=False,
            is_supervisor=True
        )
        
        # Create default employee role
        employee_role = Role.objects.create(
            company=company,
            name='Employee',
            description='Basic access to view and create records',
            is_admin=False,
            is_supervisor=False
        )
        
        # Create default team member role
        team_member_role = Role.objects.create(
            company=company,
            name='Team Member',
            description='Standard team access with collaborative permissions',
            is_admin=False,
            is_supervisor=False,
            is_team_member=True
        )
        
        # Add all permissions to admin role
        admin_permissions = []
        for resource, _ in Permission.RESOURCE_CHOICES:
            for action, _ in Permission.ACTION_CHOICES:
                admin_permissions.append(
                    Permission(role=admin_role, resource=resource, action=action)
                )
        Permission.objects.bulk_create(admin_permissions)
        
        # Add supervisor permissions (view and export mostly)
        supervisor_permissions = []
        supervisor_actions = ['view', 'export']
        for resource, _ in Permission.RESOURCE_CHOICES:
            for action in supervisor_actions:
                supervisor_permissions.append(
                    Permission(role=supervisor_role, resource=resource, action=action)
                )
        Permission.objects.bulk_create(supervisor_permissions)
        
        # Add basic employee permissions
        employee_permissions = []
        employee_resources = ['projects', 'expenses', 'contractors']
        employee_actions = ['view', 'create', 'edit']
        for resource in employee_resources:
            for action in employee_actions:
                employee_permissions.append(
                    Permission(role=employee_role, resource=resource, action=action)
                )
        Permission.objects.bulk_create(employee_permissions)
        
        # Add team member permissions (similar to employee but with some additional access)
        team_member_permissions = []
        team_member_resources = ['projects', 'expenses', 'contractors', 'reports']
        team_member_actions = ['view', 'create', 'edit', 'export']
        for resource in team_member_resources:
            for action in team_member_actions:
                team_member_permissions.append(
                    Permission(role=team_member_role, resource=resource, action=action)
                )
        Permission.objects.bulk_create(team_member_permissions)
        
        # Create company membership for admin
        CompanyMembership.objects.create(
            user=admin_user,
            company=company,
            role=admin_role,
            status='active',
            joined_date=company.created_at
        )

class RoleForm(forms.ModelForm):
    """Form for creating and editing roles"""
    permissions = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    class Meta:
        model = Role
        fields = ['name', 'description', 'is_admin', 'is_supervisor', 'is_team_member']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2})
        }
    
    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        # Build permission choices
        choices = []
        for resource, resource_label in Permission.RESOURCE_CHOICES:
            for action, action_label in Permission.ACTION_CHOICES:
                choice_key = f"{resource}_{action}"
                choice_label = f"{resource_label} - {action_label}"
                choices.append((choice_key, choice_label))
        
        self.fields['permissions'].choices = choices
        
        # Set initial permissions if editing existing role
        if self.instance.pk:
            initial_permissions = []
            for perm in self.instance.permissions.all():
                initial_permissions.append(f"{perm.resource}_{perm.action}")
            self.fields['permissions'].initial = initial_permissions
    
    def save(self, commit=True):
        role = super().save(commit=False)
        if not role.company_id:
            role.company = self.company
        
        if commit:
            role.save()
            
            # Clear existing permissions
            role.permissions.all().delete()
            
            # Add selected permissions
            permissions_to_create = []
            for perm_key in self.cleaned_data['permissions']:
                resource, action = perm_key.split('_')
                permissions_to_create.append(
                    Permission(role=role, resource=resource, action=action)
                )
            Permission.objects.bulk_create(permissions_to_create)
            
        return role

class UserInviteForm(forms.Form):
    """Form for inviting users to join a company"""
    email = forms.EmailField(help_text='Email address of the person to invite')
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    username = forms.CharField(max_length=150, help_text='Username for login (optional - will use email if not provided)', required=False)
    role = forms.ModelChoiceField(queryset=None, help_text='Role to assign to the user')
    send_credentials = forms.BooleanField(
        initial=True,
        required=False,
        help_text='Send login credentials to the user via email'
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text='Optional message to include in the invitation email'
    )
    
    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company')
        super().__init__(*args, **kwargs)
        self.fields['role'].queryset = self.company.roles.all()
    
    def clean_email(self):
        email = self.cleaned_data['email']
        # Check if user already exists in this company
        if CompanyMembership.objects.filter(
            company=self.company,
            user__email=email
        ).exists():
            raise forms.ValidationError(
                'A user with this email is already a member of this company.'
            )
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            # Check if username is already taken
            if User.objects.filter(username=username).exists():
                raise forms.ValidationError('This username is already taken.')
        return username

class UserProfileForm(forms.ModelForm):
    """Form for editing user profiles"""
    username = forms.CharField(max_length=150, help_text='Your unique username for login')
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField()
    
    class Meta:
        model = UserProfile
        fields = ['phone', 'avatar', 'notification_preferences']
        widgets = {
            'notification_preferences': forms.Textarea(attrs={'rows': 3})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['username'].initial = self.instance.user.username
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
            
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Username'
        })
        self.fields['first_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'First name'
        })
        self.fields['last_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Last name'
        })
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Email address'
        })
    
    def clean_username(self):
        username = self.cleaned_data['username']
        # Check if username is taken by another user
        if self.instance and self.instance.user:
            if User.objects.filter(username=username).exclude(id=self.instance.user.id).exists():
                raise forms.ValidationError('This username is already taken.')
        else:
            if User.objects.filter(username=username).exists():
                raise forms.ValidationError('This username is already taken.')
        return username
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            # Update user fields
            user = profile.user
            user.username = self.cleaned_data.get('username', '')
            user.first_name = self.cleaned_data.get('first_name', '')
            user.last_name = self.cleaned_data.get('last_name', '')
            user.email = self.cleaned_data.get('email', '')
            user.save()
            profile.save()
        return profile

class FlexibleAuthenticationForm(AuthenticationForm):
    """Enhanced authentication form that accepts email or username"""
    username = forms.CharField(
        max_length=254,
        widget=forms.TextInput(attrs={
            'autofocus': True,
            'class': 'form-control',
            'placeholder': 'Email or Username'
        }),
        label='Email or Username'
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'current-password',
            'class': 'form-control',
            'placeholder': 'Password'
        }),
    )
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            return username
        
        # Check if it's an email
        if '@' in username:
            # Try to find user by email
            try:
                user = User.objects.get(email=username)
                return user.username  # Return actual username for authentication
            except User.DoesNotExist:
                pass
        
        return username

class CompanyRegistrationRequestForm(forms.ModelForm):
    """Form for company registration with document upload"""
    # Basic company information
    admin_first_name = forms.CharField(max_length=30, label='Contact Person First Name')
    admin_last_name = forms.CharField(max_length=30, label='Contact Person Last Name')
    admin_email = forms.EmailField(label='Contact Person Email')
    admin_username = forms.CharField(
        max_length=150, 
        required=False,
        label='Preferred Username (optional)',
        help_text='Leave blank to use email as username'
    )
    admin_phone = forms.CharField(max_length=20, required=False, label='Contact Phone')
    
    # Document uploads
    business_registration_doc = forms.FileField(
        label='Business Registration Certificate',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        help_text='Upload your business registration certificate (PDF, JPG, PNG)'
    )
    tax_certificate_doc = forms.FileField(
        label='Tax Registration Certificate',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        help_text='Upload your tax registration certificate (PDF, JPG, PNG)',
        required=False
    )
    cac_certificate_doc = forms.FileField(
        label='CAC Certificate',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        help_text='Upload your CAC certificate (PDF, JPG, PNG)',
        required=False
    )
    director_id_doc = forms.FileField(
        label='Director ID Document',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        help_text='Upload director/owner ID document (PDF, JPG, PNG)'
    )
    utility_bill_doc = forms.FileField(
        label='Utility Bill',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        help_text='Upload recent utility bill as proof of address (PDF, JPG, PNG)',
        required=False
    )
    
    terms_accepted = forms.BooleanField(
        required=True,
        label='I agree to the Terms of Service and Privacy Policy'
    )
    
    class Meta:
        model = AccountActivationRequest
        fields = [
            'company_name', 'company_description', 'company_website', 
            'company_address', 'company_registration_number'
        ]
        widgets = {
            'company_description': forms.Textarea(attrs={'rows': 3}),
            'company_address': forms.Textarea(attrs={'rows': 2}),
        }
        labels = {
            'company_name': 'Company Name',
            'company_description': 'Company Description',
            'company_website': 'Company Website (optional)',
            'company_address': 'Company Address',
            'company_registration_number': 'Company Registration Number',
        }
    
    def clean_admin_email(self):
        email = self.cleaned_data['admin_email']
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        # Check if there's already a pending request
        if AccountActivationRequest.objects.filter(
            email=email, 
            status__in=['pending', 'under_review', 'documents_required']
        ).exists():
            raise forms.ValidationError('A registration request with this email is already pending.')
        return email
    
    def clean_admin_username(self):
        username = self.cleaned_data.get('admin_username')
        if username and User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username
    
    def clean_company_name(self):
        name = self.cleaned_data['company_name']
        # Check if company name is already taken
        if Company.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError('A company with this name already exists.')
        # Check if there's already a pending request for this company
        if AccountActivationRequest.objects.filter(
            company_name__iexact=name,
            status__in=['pending', 'under_review', 'documents_required']
        ).exists():
            raise forms.ValidationError('A registration request for this company is already pending.')
        return name
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate file sizes (max 10MB each)
        file_fields = [
            'business_registration_doc', 'tax_certificate_doc', 'cac_certificate_doc',
            'director_id_doc', 'utility_bill_doc'
        ]
        
        for field_name in file_fields:
            file_obj = cleaned_data.get(field_name)
            if file_obj and hasattr(file_obj, 'size'):
                if file_obj.size > 10 * 1024 * 1024:  # 10MB
                    self.add_error(field_name, 'File size cannot exceed 10MB.')
        
        return cleaned_data
    
    @transaction.atomic
    def save(self, commit=True):
        # Create activation request
        activation_request = super().save(commit=False)
        activation_request.request_type = 'company_registration'
        activation_request.email = self.cleaned_data['admin_email']
        activation_request.username = self.cleaned_data.get('admin_username') or self.cleaned_data['admin_email']
        activation_request.first_name = self.cleaned_data['admin_first_name']
        activation_request.last_name = self.cleaned_data['admin_last_name']
        activation_request.phone = self.cleaned_data.get('admin_phone', '')
        activation_request.activation_token = secrets.token_urlsafe(32)
        activation_request.expires_at = timezone.now() + timedelta(days=30)  # 30 days expiry
        
        if commit:
            activation_request.save()
            
            # Save uploaded documents
            self._save_documents(activation_request)
            
        return activation_request
    
    def _save_documents(self, activation_request):
        """Save uploaded documents"""
        document_mappings = {
            'business_registration_doc': 'business_registration',
            'tax_certificate_doc': 'tax_certificate',
            'cac_certificate_doc': 'cac_certificate',
            'director_id_doc': 'director_id',
            'utility_bill_doc': 'utility_bill',
        }
        
        for field_name, doc_type in document_mappings.items():
            file_obj = self.cleaned_data.get(field_name)
            if file_obj:
                DocumentUpload.objects.create(
                    activation_request=activation_request,
                    document_type=doc_type,
                    file=file_obj,
                    original_filename=file_obj.name,
                    file_size=file_obj.size
                )

class IndividualRegistrationRequestForm(forms.ModelForm):
    """Form for individual registration with document upload"""
    # Personal information
    username = forms.CharField(
        max_length=150,
        required=False,
        label='Preferred Username (optional)',
        help_text='Leave blank to use email as username'
    )
    phone = forms.CharField(max_length=20, required=False, label='Phone Number')
    address = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False,
        label='Address'
    )
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        label='Date of Birth'
    )
    
    # Document uploads
    id_document = forms.FileField(
        label='Government ID Document',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        help_text='Upload your government-issued ID (PDF, JPG, PNG)'
    )
    passport_doc = forms.FileField(
        label='Passport (if available)',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        help_text='Upload your passport (PDF, JPG, PNG)',
        required=False
    )
    license_doc = forms.FileField(
        label='Professional License (if applicable)',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        help_text='Upload professional license if applicable (PDF, JPG, PNG)',
        required=False
    )
    
    terms_accepted = forms.BooleanField(
        required=True,
        label='I agree to the Terms of Service and Privacy Policy'
    )
    
    class Meta:
        model = AccountActivationRequest
        fields = ['first_name', 'last_name', 'email']
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'email': 'Email Address',
        }
    
    def clean_email(self):
        email = self.cleaned_data['email']
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        # Check if there's already a pending request
        if AccountActivationRequest.objects.filter(
            email=email,
            status__in=['pending', 'under_review', 'documents_required']
        ).exists():
            raise forms.ValidationError('A registration request with this email is already pending.')
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate file sizes (max 10MB each)
        file_fields = ['id_document', 'passport_doc', 'license_doc']
        
        for field_name in file_fields:
            file_obj = cleaned_data.get(field_name)
            if file_obj and hasattr(file_obj, 'size'):
                if file_obj.size > 10 * 1024 * 1024:  # 10MB
                    self.add_error(field_name, 'File size cannot exceed 10MB.')
        
        return cleaned_data
    
    @transaction.atomic
    def save(self, commit=True):
        # Create activation request
        activation_request = super().save(commit=False)
        activation_request.request_type = 'individual_registration'
        activation_request.username = self.cleaned_data.get('username') or self.cleaned_data['email']
        activation_request.phone = self.cleaned_data.get('phone', '')
        activation_request.activation_token = secrets.token_urlsafe(32)
        activation_request.expires_at = timezone.now() + timedelta(days=30)  # 30 days expiry
        
        # Store additional data in metadata
        activation_request.metadata = {
            'address': self.cleaned_data.get('address', ''),
            'date_of_birth': self.cleaned_data.get('date_of_birth').isoformat() if self.cleaned_data.get('date_of_birth') else None
        }
        
        if commit:
            activation_request.save()
            
            # Save uploaded documents
            self._save_documents(activation_request)
            
        return activation_request
    
    def _save_documents(self, activation_request):
        """Save uploaded documents"""
        document_mappings = {
            'id_document': 'individual_id',
            'passport_doc': 'passport',
            'license_doc': 'license',
        }
        
        for field_name, doc_type in document_mappings.items():
            file_obj = self.cleaned_data.get(field_name)
            if file_obj:
                DocumentUpload.objects.create(
                    activation_request=activation_request,
                    document_type=doc_type,
                    file=file_obj,
                    original_filename=file_obj.name,
                    file_size=file_obj.size
                )
