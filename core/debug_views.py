from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib.auth.models import User
from .models import SuperOwner, UserProfile


@login_required
def user_permissions_debug(request):
    """Debug view to check user permissions"""
    
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponse("Access denied. Only staff users can access this debug view.")
    
    user = request.user
    debug_info = []
    
    # Basic user info
    debug_info.append(f"Username: {user.username}")
    debug_info.append(f"Email: {user.email}")
    debug_info.append(f"Is Staff: {user.is_staff}")
    debug_info.append(f"Is Superuser: {user.is_superuser}")
    debug_info.append("---")
    
    # UserProfile info
    try:
        profile = user.userprofile
        debug_info.append("UserProfile exists: Yes")
        debug_info.append(f"Account Type: {profile.account_type}")
        debug_info.append(f"Is Verified: {profile.is_verified}")
        debug_info.append(f"Is Account Active: {profile.is_account_active}")
        debug_info.append(f"Is Super Owner: {profile.is_super_owner()}")
        debug_info.append(f"Can Access Django Admin: {profile.can_access_django_admin()}")
    except UserProfile.DoesNotExist:
        debug_info.append("UserProfile exists: No")
    
    debug_info.append("---")
    
    # SuperOwner info
    try:
        super_owner = user.super_owner_profile
        debug_info.append("SuperOwner profile exists: Yes")
        debug_info.append(f"Is Primary Owner: {super_owner.is_primary_owner}")
        debug_info.append(f"Delegation Level: {super_owner.delegation_level}")
        debug_info.append(f"Can Manage Companies: {super_owner.can_manage_companies}")
        debug_info.append(f"Can Manage Users: {super_owner.can_manage_users}")
        debug_info.append(f"Can Activate Accounts: {super_owner.can_activate_accounts}")
        debug_info.append(f"Can Access Django Admin: {super_owner.can_access_django_admin}")
        debug_info.append(f"Can Delegate Permissions: {super_owner.can_delegate_permissions}")
        debug_info.append(f"Can View System Analytics: {super_owner.can_view_system_analytics}")
        
        allowed_companies = super_owner.allowed_companies.all()
        if allowed_companies.exists():
            debug_info.append(f"Allowed Companies: {', '.join([c.name for c in allowed_companies])}")
        else:
            debug_info.append("Allowed Companies: All (no restrictions)")
            
    except AttributeError:
        debug_info.append("SuperOwner profile exists: No")
    
    debug_info.append("---")
    
    # Company memberships
    memberships = user.company_memberships.all()
    if memberships.exists():
        debug_info.append("Company Memberships:")
        for membership in memberships:
            debug_info.append(f"  - {membership.company.name}: {membership.role.name if membership.role else 'No Role'} ({membership.status})")
    else:
        debug_info.append("Company Memberships: None")
    
    # Return as plain text for easy reading
    return HttpResponse(
        "\n".join(debug_info),
        content_type="text/plain"
    )


@login_required
def all_users_permissions_debug(request):
    """Debug view to check all users' permissions"""
    
    if not request.user.is_superuser:
        return HttpResponse("Access denied. Only superusers can access this debug view.")
    
    debug_info = []
    debug_info.append("ALL USERS PERMISSIONS DEBUG")
    debug_info.append("=" * 50)
    
    # Get all users
    users = User.objects.all().select_related('userprofile').prefetch_related('super_owner_profile', 'company_memberships__company', 'company_memberships__role')
    
    for user in users:
        debug_info.append(f"\nUser: {user.username} ({user.email})")
        debug_info.append(f"Staff: {user.is_staff}, Superuser: {user.is_superuser}")
        
        # UserProfile
        try:
            profile = user.userprofile
            debug_info.append(f"Profile: {profile.account_type}, Super Owner: {profile.is_super_owner()}")
        except UserProfile.DoesNotExist:
            debug_info.append("Profile: None")
        
        # SuperOwner
        try:
            super_owner = user.super_owner_profile
            permissions = []
            if super_owner.can_manage_companies:
                permissions.append("Companies")
            if super_owner.can_manage_users:
                permissions.append("Users")
            if super_owner.can_activate_accounts:
                permissions.append("Activations")
            if super_owner.can_access_django_admin:
                permissions.append("Django Admin")
            debug_info.append(f"Super Owner: {', '.join(permissions) if permissions else 'No permissions'}")
        except AttributeError:
            debug_info.append("Super Owner: No")
        
        # Company memberships
        memberships = user.company_memberships.filter(status='active')
        if memberships.exists():
            companies = [f"{m.company.name}({m.role.name if m.role else 'No Role'})" for m in memberships]
            debug_info.append(f"Companies: {', '.join(companies)}")
        else:
            debug_info.append("Companies: None")
        
        debug_info.append("-" * 30)
    
    return HttpResponse(
        "\n".join(debug_info),
        content_type="text/plain"
    )
