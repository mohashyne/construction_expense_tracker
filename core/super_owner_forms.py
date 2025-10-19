from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import SuperOwner, AccountActivationRequest, Company


class SuperOwnerForm(forms.ModelForm):
    """Form for creating and editing super owner delegations"""
    
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Select user to grant super owner access"
    )
    
    class Meta:
        model = SuperOwner
        fields = [
            'user', 'delegation_level', 'can_manage_companies', 
            'can_manage_users', 'can_activate_accounts', 
            'can_access_django_admin', 'can_delegate_permissions',
            'can_manage_billing', 'can_view_system_analytics',
            'allowed_companies'
        ]
        widgets = {
            'delegation_level': forms.Select(attrs={'class': 'form-control'}),
            'allowed_companies': forms.CheckboxSelectMultiple(),
        }
        help_texts = {
            'delegation_level': 'Choose the level of access to grant',
            'can_manage_companies': 'Allow managing all companies or specific ones',
            'can_manage_users': 'Allow managing users across the system',
            'can_activate_accounts': 'Allow approving account activation requests',
            'can_access_django_admin': 'Allow access to Django admin interface',
            'can_delegate_permissions': 'Allow creating other super owners',
            'can_manage_billing': 'Allow managing billing and subscriptions',
            'can_view_system_analytics': 'Allow viewing system-wide analytics',
            'allowed_companies': 'Leave empty to allow access to all companies',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes
        for field_name, field in self.fields.items():
            if field_name not in ['allowed_companies']:
                field.widget.attrs.update({'class': 'form-control'})
        
        # Exclude users who are already super owners
        existing_super_owners = SuperOwner.objects.values_list('user_id', flat=True)
        self.fields['user'].queryset = User.objects.filter(
            is_active=True
        ).exclude(id__in=existing_super_owners)
    
    def clean_user(self):
        user = self.cleaned_data['user']
        
        # Check if user already has super owner access
        if SuperOwner.objects.filter(user=user).exists():
            raise ValidationError('This user already has super owner access.')
        
        return user
    
    def save(self, commit=True):
        super_owner = super().save(commit=False)
        
        # Set permissions based on delegation level
        if super_owner.delegation_level == 'full':
            super_owner.can_manage_companies = True
            super_owner.can_manage_users = True
            super_owner.can_activate_accounts = True
            super_owner.can_access_django_admin = True
            super_owner.can_delegate_permissions = True
            super_owner.can_manage_billing = True
            super_owner.can_view_system_analytics = True
        elif super_owner.delegation_level == 'company_management':
            super_owner.can_manage_companies = True
            super_owner.can_manage_users = False
            super_owner.can_activate_accounts = False
            super_owner.can_access_django_admin = False
            super_owner.can_delegate_permissions = False
            super_owner.can_manage_billing = False
            super_owner.can_view_system_analytics = True
        elif super_owner.delegation_level == 'user_management':
            super_owner.can_manage_companies = False
            super_owner.can_manage_users = True
            super_owner.can_activate_accounts = True
            super_owner.can_access_django_admin = False
            super_owner.can_delegate_permissions = False
            super_owner.can_manage_billing = False
            super_owner.can_view_system_analytics = False
        elif super_owner.delegation_level == 'billing_management':
            super_owner.can_manage_companies = False
            super_owner.can_manage_users = False
            super_owner.can_activate_accounts = False
            super_owner.can_access_django_admin = False
            super_owner.can_delegate_permissions = False
            super_owner.can_manage_billing = True
            super_owner.can_view_system_analytics = True
        elif super_owner.delegation_level == 'read_only':
            super_owner.can_manage_companies = False
            super_owner.can_manage_users = False
            super_owner.can_activate_accounts = False
            super_owner.can_access_django_admin = False
            super_owner.can_delegate_permissions = False
            super_owner.can_manage_billing = False
            super_owner.can_view_system_analytics = True
        
        if commit:
            super_owner.save()
            self.save_m2m()
        
        return super_owner


class AccountActivationForm(forms.ModelForm):
    """Form for creating account activation requests"""
    
    class Meta:
        model = AccountActivationRequest
        fields = [
            'request_type', 'email', 'first_name', 'last_name', 'phone',
            'company_name', 'company_description', 'company_website',
            'target_company', 'requested_role'
        ]
        widgets = {
            'request_type': forms.Select(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'company_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'company_website': forms.URLInput(attrs={'class': 'form-control'}),
            'target_company': forms.Select(attrs={'class': 'form-control'}),
            'requested_role': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make fields conditional based on request type
        self.fields['target_company'].queryset = Company.objects.filter(is_active=True)
    
    def clean(self):
        cleaned_data = super().clean()
        request_type = cleaned_data.get('request_type')
        
        if request_type == 'company_registration':
            # Company registration requires company details
            required_fields = ['company_name', 'company_description']
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, f'This field is required for {request_type}.')
        
        elif request_type == 'user_invitation':
            # User invitation requires target company
            if not cleaned_data.get('target_company'):
                self.add_error('target_company', 'Target company is required for user invitations.')
        
        return cleaned_data


class CompanyActivationForm(forms.Form):
    """Form for activating/deactivating companies"""
    
    is_active = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Company Active'
    )
    
    subscription_type = forms.ChoiceField(
        choices=Company.SUBSCRIPTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Subscription Type'
    )
    
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        label='Admin Notes',
        help_text='Internal notes about this action'
    )


class BulkUserActionForm(forms.Form):
    """Form for bulk actions on users"""
    
    ACTION_CHOICES = [
        ('activate', 'Activate Selected Users'),
        ('deactivate', 'Deactivate Selected Users'),
        ('delete', 'Delete Selected Users'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Action to Perform'
    )
    
    selected_users = forms.CharField(
        widget=forms.HiddenInput(),
        label='Selected Users (IDs)'
    )
    
    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='I confirm this action'
    )
    
    def clean_selected_users(self):
        user_ids = self.cleaned_data['selected_users']
        try:
            # Convert comma-separated IDs to list of integers
            user_ids = [int(id.strip()) for id in user_ids.split(',') if id.strip()]
            
            # Validate that all IDs exist
            existing_count = User.objects.filter(id__in=user_ids).count()
            if existing_count != len(user_ids):
                raise ValidationError('Some selected users do not exist.')
            
            return user_ids
        except ValueError:
            raise ValidationError('Invalid user ID format.')


class SystemSettingsForm(forms.Form):
    """Form for system-wide settings that super owners can control"""
    
    allow_self_registration = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Allow Self Registration',
        help_text='Allow users to register without super owner approval'
    )
    
    allow_company_creation = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Allow Company Creation',
        help_text='Allow users to create new companies'
    )
    
    default_trial_days = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label='Default Trial Period (Days)',
        help_text='Number of days for trial subscriptions',
        min_value=1,
        max_value=365,
        initial=30
    )
    
    max_users_per_company = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label='Max Users Per Company',
        help_text='Maximum number of users allowed per company (0 = unlimited)',
        min_value=0,
        initial=0
    )
    
    system_maintenance_mode = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Maintenance Mode',
        help_text='Enable system-wide maintenance mode'
    )
    
    maintenance_message = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        label='Maintenance Message',
        help_text='Message to display during maintenance'
    )


class SuperOwnerEditForm(SuperOwnerForm):
    """Form for editing existing super owner permissions"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make user field read-only when editing
        if self.instance.pk:
            self.fields['user'].disabled = True
            self.fields['user'].help_text = "User cannot be changed after creation"
    
    def clean_user(self):
        # Skip validation when editing existing super owner
        if self.instance.pk:
            return self.instance.user
        return super().clean_user()
