from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from .models import CompanyMembership, UserProfile

class MultiTenantMiddleware(MiddlewareMixin):
    """
    Middleware to enforce multi-tenant access control.
    Sets the current company context for each request.
    """
    
    def process_request(self, request):
        # Skip for anonymous users and certain URLs
        if not request.user.is_authenticated:
            return None
            
        exempt_urls = [
            '/admin/', '/auth/', '/static/', '/media/',
            '/company/register/', '/company/switch/', '/invitation/',
            '/super-owner/'  # Exempt super owner URLs
        ]
        
        if any(request.path.startswith(url) for url in exempt_urls):
            return None
        
        # Skip company requirement for super owners
        try:
            if hasattr(request.user, 'userprofile') and request.user.userprofile.is_super_owner():
                return None
        except:
            pass
        
        # Get or set current company
        current_company = self.get_current_company(request)
        if not current_company and request.path not in ['/dashboard/', '/']:
            # Redirect to company selection if no company is set
            messages.warning(request, 'Please select a company to continue')
            return redirect('dashboard:dashboard')
        
        # Set company in request for easy access
        request.current_company = current_company
        
        # Get user's membership for permission checking
        if current_company:
            try:
                membership = CompanyMembership.objects.get(
                    user=request.user,
                    company=current_company,
                    status='active'
                )
                request.company_membership = membership
            except CompanyMembership.DoesNotExist:
                # User doesn't have access to this company
                messages.error(request, 'Access denied to this company')
                return redirect('dashboard:dashboard')
        
        return None
    
    def get_current_company(self, request):
        """Get user's current active company"""
        try:
            profile = request.user.userprofile
            if profile.last_company:
                # Verify user still has access to this company
                if CompanyMembership.objects.filter(
                    user=request.user,
                    company=profile.last_company,
                    status='active'
                ).exists():
                    return profile.last_company
        except UserProfile.DoesNotExist:
            pass
        
        # Get first active membership
        membership = CompanyMembership.objects.filter(
            user=request.user, 
            status='active'
        ).first()
        
        if membership:
            return membership.company
        return None

class PermissionMiddleware(MiddlewareMixin):
    """
    Middleware to check permissions for specific views.
    """
    
    # Define which URLs require specific permissions
    PERMISSION_MAP = {
        '/projects/create/': ('projects', 'create'),
        '/projects/edit/': ('projects', 'edit'),
        '/projects/delete/': ('projects', 'delete'),
        '/expenses/create/': ('expenses', 'create'),
        '/expenses/edit/': ('expenses', 'edit'),
        '/expenses/delete/': ('expenses', 'delete'),
        '/expenses/approve/': ('expenses', 'approve'),
        '/contractors/create/': ('contractors', 'create'),
        '/contractors/edit/': ('contractors', 'edit'),
        '/contractors/delete/': ('contractors', 'delete'),
        '/reports/': ('reports', 'view'),
        '/reports/export/': ('reports', 'export'),
        '/company/manage/': ('company', 'edit'),
        '/company/users/': ('users', 'view'),
        '/company/billing/': ('billing', 'view'),
    }
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Skip for anonymous users
        if not request.user.is_authenticated:
            return None
        
        # Skip if no company context
        if not hasattr(request, 'company_membership'):
            return None
        
        membership = request.company_membership
        
        # Check for specific URL patterns that require permissions
        for url_pattern, (resource, action) in self.PERMISSION_MAP.items():
            if request.path.startswith(url_pattern):
                if not membership.has_permission(resource, action):
                    messages.error(request, f'Access denied. Missing permission: {action} {resource}')
                    return redirect('dashboard:dashboard')
        
        # Special checks for admin-only views
        admin_only_patterns = ['/company/manage/', '/company/users/', '/roles/']
        if any(request.path.startswith(pattern) for pattern in admin_only_patterns):
            if not membership.is_company_admin():
                messages.error(request, 'Access denied. Administrator privileges required.')
                return redirect('dashboard:dashboard')
        
        # Special checks for supervisor views
        supervisor_patterns = ['/supervisor/', '/executive/']
        if any(request.path.startswith(pattern) for pattern in supervisor_patterns):
            if not (membership.is_company_supervisor() or membership.is_company_admin()):
                messages.error(request, 'Access denied. Supervisor privileges required.')
                return redirect('dashboard:dashboard')
        
        return None

def get_user_permissions(user, company):
    """
    Utility function to get all permissions for a user in a company.
    Returns a set of permission strings in format 'resource.action'
    """
    try:
        membership = CompanyMembership.objects.get(
            user=user,
            company=company,
            status='active'
        )
        
        if not membership.role:
            return set()
        
        permissions = set()
        for perm in membership.role.permissions.all():
            permissions.add(f"{perm.resource}.{perm.action}")
        
        return permissions
        
    except CompanyMembership.DoesNotExist:
        return set()

def user_has_permission(user, company, resource, action):
    """
    Check if user has a specific permission in a company.
    """
    try:
        membership = CompanyMembership.objects.get(
            user=user,
            company=company,
            status='active'
        )
        return membership.has_permission(resource, action)
    except CompanyMembership.DoesNotExist:
        return False

def require_permission(resource, action):
    """
    Decorator to require specific permissions for a view.
    Usage: @require_permission('projects', 'create')
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('core:login')
            
            if not hasattr(request, 'current_company') or not request.current_company:
                messages.error(request, 'No company selected')
                return redirect('dashboard:dashboard')
            
            if not user_has_permission(request.user, request.current_company, resource, action):
                messages.error(request, f'Access denied. Missing permission: {action} {resource}')
                return redirect('dashboard:dashboard')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def require_admin(view_func):
    """
    Decorator to require admin privileges.
    """
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('core:login')
        
        if not hasattr(request, 'company_membership'):
            messages.error(request, 'No company membership found')
            return redirect('dashboard:dashboard')
        
        if not request.company_membership.is_company_admin():
            messages.error(request, 'Access denied. Administrator privileges required.')
            return redirect('dashboard:dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper

def require_supervisor(view_func):
    """
    Decorator to require supervisor privileges.
    """
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('core:login')
        
        if not hasattr(request, 'company_membership'):
            messages.error(request, 'No company membership found')
            return redirect('dashboard:dashboard')
        
        membership = request.company_membership
        if not (membership.is_company_supervisor() or membership.is_company_admin()):
            messages.error(request, 'Access denied. Supervisor privileges required.')
            return redirect('dashboard:dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper
