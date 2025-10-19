from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import (
    Company, Role, Permission, CompanyMembership, 
    UserProfile, Notification, NotificationTemplate, UserNotificationPreference,
    SuperOwner, AccountActivationRequest, DocumentUpload
)

# Custom admin site access control
class SuperOwnerAccessMixin:
    """Mixin to control admin access based on SuperOwner permissions"""
    
    def has_module_permission(self, request):
        """Check if user can access this admin module"""
        if not super().has_module_permission(request):
            return False
        
        # Always allow superusers
        if request.user.is_superuser:
            return True
        
        # Check if user is super owner with admin access
        if hasattr(request.user, 'userprofile'):
            try:
                return request.user.userprofile.can_access_django_admin()
            except:
                return False
        
        return False
    
    def has_view_permission(self, request, obj=None):
        if not self.has_module_permission(request):
            return False
        return super().has_view_permission(request, obj)
    
    def has_add_permission(self, request):
        if not self.has_module_permission(request):
            return False
        return super().has_add_permission(request)
    
    def has_change_permission(self, request, obj=None):
        if not self.has_module_permission(request):
            return False
        return super().has_change_permission(request, obj)
    
    def has_delete_permission(self, request, obj=None):
        if not self.has_module_permission(request):
            return False
        return super().has_delete_permission(request, obj)

@admin.register(Company)
class CompanyAdmin(SuperOwnerAccessMixin, admin.ModelAdmin):
    list_display = ['name', 'slug', 'email', 'subscription_type', 'is_active', 'created_at']
    list_filter = ['subscription_type', 'is_active', 'created_at']
    search_fields = ['name', 'email', 'slug']
    readonly_fields = ['created_at', 'updated_at']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Role)
class RoleAdmin(SuperOwnerAccessMixin, admin.ModelAdmin):
    list_display = ['name', 'company', 'is_admin', 'is_supervisor', 'created_at']
    list_filter = ['company', 'is_admin', 'is_supervisor']
    search_fields = ['name', 'company__name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Permission)
class PermissionAdmin(SuperOwnerAccessMixin, admin.ModelAdmin):
    list_display = ['role', 'resource', 'action']
    list_filter = ['resource', 'action', 'role__company']
    search_fields = ['role__name', 'role__company__name']

@admin.register(CompanyMembership)
class CompanyMembershipAdmin(SuperOwnerAccessMixin, admin.ModelAdmin):
    list_display = ['user', 'company', 'role', 'status', 'joined_date']
    list_filter = ['status', 'role', 'company']
    search_fields = ['user__username', 'user__email', 'company__name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(UserProfile)
class UserProfileAdmin(SuperOwnerAccessMixin, admin.ModelAdmin):
    list_display = ['user', 'phone', 'last_company', 'created_at']
    list_filter = ['last_company', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(SuperOwnerAccessMixin, admin.ModelAdmin):
    list_display = ['name', 'company', 'notification_type', 'control_level', 'default_priority', 'is_active']
    list_filter = ['company', 'notification_type', 'control_level', 'default_priority', 'is_active']
    search_fields = ['name', 'company__name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['allowed_roles']

@admin.register(UserNotificationPreference)
class UserNotificationPreferenceAdmin(SuperOwnerAccessMixin, admin.ModelAdmin):
    list_display = ['user', 'company', 'notification_template', 'in_app_enabled', 'email_enabled', 'sms_enabled', 'is_enabled']
    list_filter = ['company', 'notification_template__notification_type', 'in_app_enabled', 'email_enabled', 'sms_enabled', 'is_enabled']
    search_fields = ['user__username', 'company__name', 'notification_template__name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Notification)
class NotificationAdmin(SuperOwnerAccessMixin, admin.ModelAdmin):
    list_display = ['title', 'recipient', 'company', 'priority', 'in_app_status', 'email_status', 'sms_status', 'created_at']
    list_filter = ['notification_template__notification_type', 'priority', 'in_app_status', 'email_status', 'sms_status', 'company', 'created_at']
    search_fields = ['title', 'recipient__username', 'company__name', 'message']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('recipient', 'company', 'sender', 'notification_template')


@admin.register(SuperOwner)
class SuperOwnerAdmin(SuperOwnerAccessMixin, admin.ModelAdmin):
    list_display = [
        'user_info', 'is_primary_owner', 'delegation_level', 
        'permissions_summary', 'created_by', 'created_at'
    ]
    list_filter = [
        'is_primary_owner', 'delegation_level', 'can_manage_companies',
        'can_manage_users', 'can_activate_accounts', 'can_access_django_admin',
        'created_at'
    ]
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    filter_horizontal = ['allowed_companies']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'is_primary_owner', 'delegation_level')
        }),
        ('Permissions', {
            'fields': (
                'can_manage_companies', 'can_manage_users', 'can_activate_accounts',
                'can_access_django_admin', 'can_delegate_permissions',
                'can_manage_billing', 'can_view_system_analytics'
            )
        }),
        ('Restrictions', {
            'fields': ('allowed_companies',)
        }),
        ('System Info', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def user_info(self, obj):
        return format_html(
            '<strong>{}</strong><br/><small>{}</small>',
            obj.user.get_full_name() or obj.user.username,
            obj.user.email
        )
    user_info.short_description = 'User'
    
    def permissions_summary(self, obj):
        permissions = []
        if obj.can_manage_companies:
            permissions.append('Companies')
        if obj.can_manage_users:
            permissions.append('Users')
        if obj.can_activate_accounts:
            permissions.append('Activations')
        if obj.can_access_django_admin:
            permissions.append('Django Admin')
        if obj.can_delegate_permissions:
            permissions.append('Delegation')
        if obj.can_manage_billing:
            permissions.append('Billing')
        if obj.can_view_system_analytics:
            permissions.append('Analytics')
        
        return ', '.join(permissions) if permissions else 'None'
    permissions_summary.short_description = 'Permissions'
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'created_by')


@admin.register(AccountActivationRequest)
class AccountActivationRequestAdmin(SuperOwnerAccessMixin, admin.ModelAdmin):
    list_display = [
        'email', 'request_type', 'status', 'requester_name', 
        'company_name', 'created_at', 'action_buttons'
    ]
    list_filter = [
        'request_type', 'status', 'created_at', 'expires_at'
    ]
    search_fields = [
        'email', 'first_name', 'last_name', 'company_name', 
        'target_company__name'
    ]
    readonly_fields = [
        'id', 'activation_token', 'created_at', 'updated_at',
        'approved_by', 'approved_at'
    ]
    
    fieldsets = (
        ('Request Information', {
            'fields': ('request_type', 'status', 'email', 'first_name', 'last_name', 'phone')
        }),
        ('Company Information', {
            'fields': ('company_name', 'company_description', 'company_website'),
            'classes': ('collapse',)
        }),
        ('User Information', {
            'fields': ('target_company', 'requested_role', 'invited_by'),
            'classes': ('collapse',)
        }),
        ('Approval Information', {
            'fields': ('approved_by', 'approved_at', 'rejection_reason')
        }),
        ('System Information', {
            'fields': ('id', 'activation_token', 'expires_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def requester_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    requester_name.short_description = 'Name'
    
    def action_buttons(self, obj):
        if obj.status == 'pending':
            # Redirect to super owner dashboard for management
            detail_url = f'/super-owner/registration-requests/{obj.id}/'
            return format_html(
                '<a href="{}" class="button" target="_blank">Manage in Super Owner Dashboard</a>',
                detail_url
            )
        return obj.get_status_display()
    action_buttons.short_description = 'Actions'
    
    def get_urls(self):
        from django.urls import path, re_path
        urls = super().get_urls()
        
        # Override the change view URL to handle UUID properly
        info = self.model._meta.app_label, self.model._meta.model_name
        custom_urls = [
            re_path(
                r'^(.+)/change/$',
                self.admin_site.admin_view(self.change_view),
                name='%s_%s_change' % info,
            ),
        ]
        return custom_urls + urls[1:]  # Skip the default change URL
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Custom change view that redirects to super owner dashboard"""
        try:
            # Verify the object exists
            obj = self.get_object(request, object_id)
            if obj is None:
                raise self.model.DoesNotExist
            
            # Redirect to super owner dashboard for management
            messages.info(request, f'Managing activation request for {obj.email} in Super Owner Dashboard.')
            from django.shortcuts import redirect
            return redirect(f'/super-owner/registration-requests/{obj.id}/')
            
        except self.model.DoesNotExist:
            from django.http import Http404
            raise Http404(f'Activation request with ID "{object_id}" does not exist.')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'target_company', 'invited_by', 'approved_by'
        )


# Update existing admin classes to use SuperOwnerAccessMixin
class CompanyAdmin(SuperOwnerAccessMixin, admin.ModelAdmin):
    list_display = ['name', 'slug', 'email', 'subscription_type', 'is_active', 'created_at']
    list_filter = ['subscription_type', 'is_active', 'created_at']
    search_fields = ['name', 'email', 'slug']
    readonly_fields = ['created_at', 'updated_at']
    prepopulated_fields = {'slug': ('name',)}

# Re-register with the mixin
admin.site.unregister(Company)
admin.site.register(Company, CompanyAdmin)


# Extended User Admin with SuperOwner integration
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    

class SuperOwnerInline(admin.StackedInline):
    model = SuperOwner
    can_delete = False
    verbose_name_plural = 'Super Owner Access'
    extra = 0
    fk_name = 'user'
    
    def has_add_permission(self, request, obj):
        # Only primary super owner can add super owner access
        if hasattr(request.user, 'userprofile'):
            profile = request.user.userprofile
            if profile.is_super_owner():
                return profile.user.super_owner_profile.can_delegate_permissions
        return request.user.is_superuser


class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline, SuperOwnerInline)
    
    def get_inline_instances(self, request, obj=None):
        inline_instances = []
        
        # Always show UserProfile
        inline_instances.append(UserProfileInline(self.model, self.admin_site))
        
        # Only show SuperOwner inline if user has permission
        if obj and (request.user.is_superuser or 
                   (hasattr(request.user, 'userprofile') and 
                    request.user.userprofile.is_super_owner() and
                    request.user.super_owner_profile.can_delegate_permissions)):
            inline_instances.append(SuperOwnerInline(self.model, self.admin_site))
        
        return inline_instances

@admin.register(DocumentUpload)
class DocumentUploadAdmin(SuperOwnerAccessMixin, admin.ModelAdmin):
    list_display = [
        'document_info', 'activation_request', 'status', 
        'file_size_mb', 'reviewed_by', 'created_at'
    ]
    list_filter = [
        'document_type', 'status', 'created_at', 'reviewed_at'
    ]
    search_fields = [
        'activation_request__email', 'original_filename', 'description'
    ]
    readonly_fields = [
        'file_size', 'created_at', 'updated_at', 'file_size_mb'
    ]
    
    fieldsets = (
        ('Document Information', {
            'fields': ('activation_request', 'document_type', 'file', 'original_filename', 'file_size', 'description')
        }),
        ('Review Status', {
            'fields': ('status', 'reviewed_by', 'reviewed_at', 'review_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def document_info(self, obj):
        return format_html(
            '<strong>{}</strong><br/><small>{}</small>',
            obj.get_document_type_display(),
            obj.original_filename
        )
    document_info.short_description = 'Document'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'activation_request', 'reviewed_by'
        )

# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
