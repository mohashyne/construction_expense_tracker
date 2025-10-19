from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
import secrets
from datetime import timedelta

from .models import (
    SuperOwner, AccountActivationRequest, Company, 
    CompanyMembership, UserProfile
)
from .super_owner_forms import SuperOwnerForm, AccountActivationForm


def is_super_owner(user):
    """Check if user is a super owner"""
    return (
        user.is_authenticated and 
        hasattr(user, 'userprofile') and 
        user.userprofile.is_super_owner()
    )


def can_activate_accounts(user):
    """Check if user can activate accounts"""
    return (
        user.is_authenticated and 
        hasattr(user, 'userprofile') and 
        user.userprofile.can_activate_accounts()
    )


@login_required
@user_passes_test(is_super_owner, login_url='/admin/login/')
def super_owner_dashboard(request):
    """Enhanced Super Owner Control Panel with comprehensive CRUD functionality"""
    
    from django.db.models import Count, Q
    from datetime import datetime, timedelta
    
    # Statistics Overview
    pending_requests = AccountActivationRequest.objects.filter(status='pending').count()
    under_review_requests = AccountActivationRequest.objects.filter(status='under_review').count()
    approved_today = AccountActivationRequest.objects.filter(
        status='approved',
        updated_at__date=datetime.now().date()
    ).count()
    rejected_today = AccountActivationRequest.objects.filter(
        status='rejected',
        updated_at__date=datetime.now().date()
    ).count()
    
    total_companies = Company.objects.count()
    total_users = User.objects.count()
    total_individuals = User.objects.filter(
        userprofile__account_type='individual'
    ).count()
    total_registrations = AccountActivationRequest.objects.count()
    
    # Registration Requests (All for comprehensive management)
    recent_requests = AccountActivationRequest.objects.select_related(
        'approved_by'
    ).prefetch_related('documents').order_by('-created_at')[:50]
    
    # Companies with full details
    companies = Company.objects.annotate(
        member_count=Count('memberships')
    ).prefetch_related(
        'memberships__user',
        'memberships__role'
    ).order_by('-created_at')[:100]
    
    # Individual Users (excluding company owners and staff)
    individual_users = User.objects.filter(
        Q(userprofile__account_type='individual') |
        Q(userprofile__account_type__isnull=True)
    ).select_related('userprofile').order_by('-date_joined')[:100]
    
    # Super Owners
    super_owners = SuperOwner.objects.select_related('user').order_by('-created_at')
    
    # Analytics Data
    approved_count = AccountActivationRequest.objects.filter(status='approved').count()
    approval_rate = (approved_count / max(total_registrations, 1)) * 100
    
    # Average processing time (mock calculation)
    avg_processing_time = 2.5  # This would be calculated from actual data
    
    # Most active company (mock data)
    most_active_company = companies.first().name if companies.exists() else None
    
    context = {
        # Statistics
        'pending_requests': pending_requests,
        'under_review_requests': under_review_requests,
        'approved_today': approved_today,
        'rejected_today': rejected_today,
        'total_companies': total_companies,
        'total_individuals': total_individuals,
        'total_users': total_users,
        'total_registrations': total_registrations,
        
        # Data for tabs
        'recent_requests': recent_requests,
        'companies': companies,
        'individual_users': individual_users,
        'super_owners': super_owners,
        
        # Analytics
        'approval_rate': approval_rate,
        'avg_processing_time': avg_processing_time,
        'most_active_company': most_active_company,
        'system_uptime': '99.9%',  # Mock data
        
        # User permissions
        'super_owner_profile': request.user.super_owner_profile,
    }
    
    return render(request, 'admin/enhanced_super_owner_dashboard.html', context)


@login_required
@user_passes_test(is_super_owner, login_url='/admin/login/')
@require_POST
def bulk_action_requests(request):
    """Handle bulk actions on registration requests"""
    import json
    
    try:
        data = json.loads(request.body)
        action = data.get('action')
        request_ids = data.get('request_ids', [])
        
        if not action or not request_ids:
            return JsonResponse({'success': False, 'message': 'Invalid data'})
        
        requests = AccountActivationRequest.objects.filter(id__in=request_ids)
        
        if action == 'approve':
            for req in requests:
                if req.status == 'pending':
                    req.status = 'approved'
                    req.approved_by = request.user
                    req.approved_at = timezone.now()
                    req.save()
                    
        elif action == 'reject':
            for req in requests:
                if req.status in ['pending', 'under_review']:
                    req.status = 'rejected'
                    req.approved_by = request.user
                    req.approved_at = timezone.now()
                    req.save()
                    
        elif action == 'review':
            for req in requests:
                if req.status == 'pending':
                    req.status = 'under_review'
                    req.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'Successfully {action}ed {len(requests)} requests'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@user_passes_test(is_super_owner, login_url='/admin/login/')
def export_data(request, data_type):
    """Export system data as CSV"""
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    
    if data_type == 'companies':
        response['Content-Disposition'] = 'attachment; filename="companies.csv"'
        writer = csv.writer(response)
        writer.writerow(['Name', 'Email', 'Description', 'Created', 'Active', 'Members'])
        
        companies = Company.objects.annotate(
            member_count=Count('memberships')
        )
        
        for company in companies:
            writer.writerow([
                company.name,
                company.email,
                company.description or '-',
                company.created_at.strftime('%Y-%m-%d'),
                'Yes' if company.is_active else 'No',
                company.member_count
            ])
            
    elif data_type == 'users':
        response['Content-Disposition'] = 'attachment; filename="users.csv"'
        writer = csv.writer(response)
        writer.writerow(['Username', 'Name', 'Email', 'Account Type', 'Joined', 'Active', 'Verified'])
        
        users = User.objects.select_related('userprofile')
        
        for user in users:
            writer.writerow([
                user.username,
                user.get_full_name() or '-',
                user.email,
                user.userprofile.get_account_type_display() if hasattr(user, 'userprofile') else 'Individual',
                user.date_joined.strftime('%Y-%m-%d'),
                'Yes' if user.is_active else 'No',
                'Yes' if hasattr(user, 'userprofile') and user.userprofile.is_verified else 'No'
            ])
            
    elif data_type == 'requests':
        response['Content-Disposition'] = 'attachment; filename="registration_requests.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date', 'Type', 'Name', 'Email', 'Company', 'Status', 'Approved By'])
        
        requests = AccountActivationRequest.objects.select_related('approved_by')
        
        for req in requests:
            writer.writerow([
                req.created_at.strftime('%Y-%m-%d'),
                req.get_request_type_display(),
                f"{req.first_name} {req.last_name}",
                req.email,
                req.company_name or '-',
                req.get_status_display(),
                req.approved_by.get_full_name() if req.approved_by else '-'
            ])
    
    return response


@login_required
@user_passes_test(can_activate_accounts, login_url='/admin/login/')
def activation_requests_list(request):
    """List all account activation requests"""
    
    status_filter = request.GET.get('status', 'pending')
    search_query = request.GET.get('search', '')
    
    requests = AccountActivationRequest.objects.all()
    
    if status_filter and status_filter != 'all':
        requests = requests.filter(status=status_filter)
    
    if search_query:
        requests = requests.filter(
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(company_name__icontains=search_query)
        )
    
    requests = requests.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(requests, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'status_choices': AccountActivationRequest.STATUS_CHOICES,
    }
    
    return render(request, 'core/super_owner/activation_requests.html', context)


@login_required
@user_passes_test(can_activate_accounts, login_url='/admin/login/')
def activation_request_detail(request, request_id):
    """View activation request details for review"""
    activation_request = get_object_or_404(AccountActivationRequest, id=request_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            try:
                activation_request.approve(request.user)
                messages.success(request, f'Activation request for {activation_request.email} has been approved.')
                return redirect('super_owner:activation_requests_list')
            except Exception as e:
                messages.error(request, f'Error approving request: {str(e)}')
                
        elif action == 'reject':
            rejection_reason = request.POST.get('rejection_reason', 'Rejected from admin')
            try:
                activation_request.reject(request.user, rejection_reason)
                messages.success(request, f'Activation request for {activation_request.email} has been rejected.')
                return redirect('super_owner:activation_requests_list')
            except Exception as e:
                messages.error(request, f'Error rejecting request: {str(e)}')
    
    context = {
        'activation_request': activation_request,
    }
    
    return render(request, 'admin/super_owner/activation_request_detail.html', context)


@login_required
@user_passes_test(can_activate_accounts, login_url='/admin/login/')
@require_POST
def approve_activation_request(request, request_id):
    """Approve an activation request"""
    
    activation_request = get_object_or_404(AccountActivationRequest, id=request_id)
    
    try:
        # Approve the request
        activation_request.approve(request.user)
        
        # Create the account based on request type
        if activation_request.request_type == 'company_registration':
            # Create company and admin user
            user = User.objects.create_user(
                username=activation_request.email,
                email=activation_request.email,
                first_name=activation_request.first_name,
                last_name=activation_request.last_name,
            )
            
            # Create user profile
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'is_account_active': True,
                    'activated_by': request.user,
                    'activated_at': timezone.now(),
                }
            )
            
            # Create company
            company = Company.objects.create(
                name=activation_request.company_name,
                slug=activation_request.company_name.lower().replace(' ', '-'),
                description=activation_request.company_description,
                email=activation_request.email,
                website=activation_request.company_website,
            )
            
            # Create admin role and membership
            from .models import Role
            admin_role = Role.objects.create(
                company=company,
                name='Company Admin',
                description='Full company administration access',
                is_admin=True,
            )
            
            CompanyMembership.objects.create(
                user=user,
                company=company,
                role=admin_role,
                status='active',
                joined_date=timezone.now(),
            )
            
        elif activation_request.request_type == 'user_invitation':
            # Create user and add to company
            user = User.objects.create_user(
                username=activation_request.email,
                email=activation_request.email,
                first_name=activation_request.first_name,
                last_name=activation_request.last_name,
            )
            
            # Create user profile
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'is_account_active': True,
                    'activated_by': request.user,
                    'activated_at': timezone.now(),
                }
            )
            
            # Add to company if specified
            if activation_request.target_company:
                CompanyMembership.objects.create(
                    user=user,
                    company=activation_request.target_company,
                    status='active',
                    joined_date=timezone.now(),
                )
        
        # Send approval notification email
        send_activation_approved_email(activation_request, user)
        
        messages.success(request, f'Activation request for {activation_request.email} has been approved.')
        
    except Exception as e:
        messages.error(request, f'Error approving request: {str(e)}')
    
    return redirect('core:activation_requests_list')


@login_required
@user_passes_test(can_activate_accounts, login_url='/admin/login/')
@require_POST
def reject_activation_request(request, request_id):
    """Reject an activation request"""
    
    activation_request = get_object_or_404(AccountActivationRequest, id=request_id)
    rejection_reason = request.POST.get('rejection_reason', '')
    
    try:
        activation_request.reject(request.user, rejection_reason)
        
        # Send rejection notification email
        send_activation_rejected_email(activation_request, rejection_reason)
        
        messages.success(request, f'Activation request for {activation_request.email} has been rejected.')
        
    except Exception as e:
        messages.error(request, f'Error rejecting request: {str(e)}')
    
    return redirect('core:activation_requests_list')


@login_required
@user_passes_test(is_super_owner, login_url='/admin/login/')
def manage_companies(request):
    """Manage all companies in the system"""
    
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', 'all')
    
    super_owner_profile = request.user.super_owner_profile
    companies = super_owner_profile.get_manageable_companies()
    
    if search_query:
        companies = companies.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    if status_filter == 'active':
        companies = companies.filter(is_active=True)
    elif status_filter == 'inactive':
        companies = companies.filter(is_active=False)
    
    # Add user counts
    companies = companies.annotate(
        user_count=Count('memberships', filter=Q(memberships__status='active'))
    ).order_by('name')
    
    # Pagination
    paginator = Paginator(companies, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'super_owner_profile': super_owner_profile,
    }
    
    return render(request, 'core/super_owner/manage_companies.html', context)


@login_required
@user_passes_test(is_super_owner, login_url='/admin/login/')
def manage_super_owners(request):
    """Manage super owner delegations"""
    
    if not request.user.super_owner_profile.can_delegate_permissions:
        messages.error(request, 'You do not have permission to manage super owner delegations.')
        return redirect('core:super_owner_dashboard')
    
    super_owners = SuperOwner.objects.all().order_by('-is_primary_owner', 'user__first_name')
    
    context = {
        'super_owners': super_owners,
    }
    
    return render(request, 'admin/super_owner/manage_super_owners.html', context)


@login_required
@user_passes_test(is_super_owner, login_url='/admin/login/')
def create_super_owner(request):
    """Create a new super owner delegation"""
    
    if not request.user.super_owner_profile.can_delegate_permissions:
        messages.error(request, 'You do not have permission to delegate super owner access.')
        return redirect('core:super_owner_dashboard')
    
    if request.method == 'POST':
        form = SuperOwnerForm(request.POST)
        if form.is_valid():
            super_owner = form.save(commit=False)
            super_owner.created_by = request.user
            super_owner.save()
            form.save_m2m()  # Save many-to-many relationships
            
            messages.success(request, f'Super owner access granted to {super_owner.user.get_full_name()}.')
            return redirect('core:manage_super_owners')
    else:
        form = SuperOwnerForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'core/super_owner/create_super_owner.html', context)


def send_activation_approved_email(activation_request, user):
    """Send email notification when activation is approved"""
    
    subject = 'Your account has been activated'
    context = {
        'activation_request': activation_request,
        'user': user,
        'login_url': settings.SITE_URL + '/login/',
    }
    
    html_message = render_to_string('core/emails/activation_approved.html', context)
    plain_message = render_to_string('core/emails/activation_approved.txt', context)
    
    send_mail(
        subject=subject,
        message=plain_message,
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[activation_request.email],
        fail_silently=False,
    )


def send_activation_rejected_email(activation_request, rejection_reason):
    """Send email notification when activation is rejected"""
    
    subject = 'Your activation request has been reviewed'
    context = {
        'activation_request': activation_request,
        'rejection_reason': rejection_reason,
        'contact_email': settings.SUPPORT_EMAIL,
    }
    
    html_message = render_to_string('core/emails/activation_rejected.html', context)
    plain_message = render_to_string('core/emails/activation_rejected.txt', context)
    
    send_mail(
        subject=subject,
        message=plain_message,
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[activation_request.email],
        fail_silently=False,
    )


# API Views for AJAX requests
@login_required
@user_passes_test(is_super_owner, login_url='/admin/login/')
def company_stats_api(request, company_id):
    """Get company statistics via AJAX"""
    
    company = get_object_or_404(Company, id=company_id)
    
    # Check if super owner can manage this company
    if not request.user.super_owner_profile.can_manage_company(company):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    stats = {
        'total_users': company.memberships.filter(status='active').count(),
        'total_projects': getattr(company, 'projects', lambda: company.projects_set).all().count() if hasattr(company, 'projects') else 0,
        'total_expenses': 0,  # Add when expense model is available
        'subscription_status': company.get_subscription_type_display(),
        'is_active': company.is_active,
        'created_at': company.created_at.strftime('%Y-%m-%d'),
    }
    
    return JsonResponse(stats)


# Enhanced CRUD Operations for Super Admin

@login_required
@user_passes_test(is_super_owner, login_url='/admin/login/')
def companies_list(request):
    """Comprehensive companies management with CRUD operations"""
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', 'all')
    
    companies = Company.objects.annotate(
        member_count=Count('memberships', filter=Q(memberships__status='active')),
        project_count=Count('project', distinct=True) if hasattr(Company, 'project') else Count('id') * 0
    ).select_related()
    
    if search_query:
        companies = companies.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    if status_filter == 'active':
        companies = companies.filter(is_active=True)
    elif status_filter == 'inactive':
        companies = companies.filter(is_active=False)
    
    companies = companies.order_by('-created_at')
    
    paginator = Paginator(companies, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_companies': Company.objects.count(),
        'active_companies': Company.objects.filter(is_active=True).count(),
    }
    
    return render(request, 'admin/super_owner/companies_list.html', context)


@login_required
@user_passes_test(is_super_owner, login_url='/admin/login/')
def company_detail(request, company_id):
    """Detailed company view with management options"""
    company = get_object_or_404(Company, id=company_id)
    memberships = company.memberships.select_related('user', 'role').order_by('-created_at')
    
    # Calculate statistics
    stats = {
        'total_members': memberships.count(),
        'active_members': memberships.filter(status='active').count(),
        'admin_members': memberships.filter(role__is_admin=True, status='active').count(),
        'subscription_status': company.get_subscription_type_display(),
    }
    
    context = {
        'company': company,
        'memberships': memberships,
        'stats': stats,
    }
    
    return render(request, 'admin/super_owner/company_detail.html', context)


@login_required
@user_passes_test(is_super_owner, login_url='/admin/login/')
def company_toggle_status(request, company_id):
    """Toggle company active status"""
    if request.method == 'POST':
        company = get_object_or_404(Company, id=company_id)
        company.is_active = not company.is_active
        company.save()
        
        action = 'activated' if company.is_active else 'deactivated'
        messages.success(request, f'Company "{company.name}" has been {action}.')
    
    return redirect('super_owner:companies_list')


@login_required
@user_passes_test(is_super_owner, login_url='/admin/login/')
def users_list(request):
    """Comprehensive users management"""
    search_query = request.GET.get('search', '')
    account_type_filter = request.GET.get('account_type', 'all')
    status_filter = request.GET.get('status', 'all')
    
    users = User.objects.select_related('userprofile').annotate(
        company_count=Count('company_memberships', filter=Q(company_memberships__status='active'))
    )
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    if account_type_filter != 'all':
        users = users.filter(userprofile__account_type=account_type_filter)
    
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    elif status_filter == 'verified':
        users = users.filter(userprofile__is_verified=True)
    elif status_filter == 'unverified':
        users = users.filter(userprofile__is_verified=False)
    
    users = users.order_by('-date_joined')
    
    paginator = Paginator(users, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'account_type_filter': account_type_filter,
        'status_filter': status_filter,
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
    }
    
    return render(request, 'admin/super_owner/users_list.html', context)


@login_required
@user_passes_test(is_super_owner, login_url='/admin/login/')
def user_detail(request, user_id):
    """Detailed user view with management options"""
    user = get_object_or_404(User, id=user_id)
    memberships = user.company_memberships.select_related('company', 'role').order_by('-created_at')
    
    # Check if user is a super owner
    is_super_owner_user = hasattr(user, 'super_owner_profile')
    
    context = {
        'user': user,
        'memberships': memberships,
        'is_super_owner_user': is_super_owner_user,
        'profile': getattr(user, 'userprofile', None),
    }
    
    return render(request, 'admin/super_owner/user_detail.html', context)


@login_required
@user_passes_test(is_super_owner, login_url='/admin/login/')
def user_toggle_status(request, user_id):
    """Toggle user active status"""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        
        # Prevent deactivating super owners
        if hasattr(user, 'super_owner_profile') and user.is_active:
            messages.error(request, 'Cannot deactivate super owner accounts.')
        else:
            user.is_active = not user.is_active
            user.save()
            
            action = 'activated' if user.is_active else 'deactivated'
            messages.success(request, f'User "{user.username}" has been {action}.')
    
    return redirect('super_owner:users_list')


@login_required
@user_passes_test(is_super_owner, login_url='/admin/login/')
def system_analytics(request):
    """System-wide analytics dashboard"""
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # System statistics
    stats = {
        # User statistics
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'new_users_week': User.objects.filter(date_joined__gte=week_ago).count(),
        'new_users_month': User.objects.filter(date_joined__gte=month_ago).count(),
        
        # Company statistics
        'total_companies': Company.objects.count(),
        'active_companies': Company.objects.filter(is_active=True).count(),
        'new_companies_week': Company.objects.filter(created_at__gte=week_ago).count(),
        'new_companies_month': Company.objects.filter(created_at__gte=month_ago).count(),
        
        # Registration statistics
        'pending_requests': AccountActivationRequest.objects.filter(status='pending').count(),
        'approved_week': AccountActivationRequest.objects.filter(
            status='approved', approved_at__gte=week_ago
        ).count(),
        'rejected_week': AccountActivationRequest.objects.filter(
            status='rejected', approved_at__gte=week_ago
        ).count(),
    }
    
    # Recent activity
    recent_users = User.objects.order_by('-date_joined')[:10]
    recent_companies = Company.objects.order_by('-created_at')[:10]
    recent_requests = AccountActivationRequest.objects.order_by('-created_at')[:10]
    
    context = {
        'stats': stats,
        'recent_users': recent_users,
        'recent_companies': recent_companies,
        'recent_requests': recent_requests,
    }
    
    return render(request, 'admin/super_owner/system_analytics.html', context)


@login_required
@user_passes_test(is_super_owner, login_url='/admin/login/')
def super_owner_profile(request):
    """Super Owner Profile Management"""
    super_owner_profile = request.user.super_owner_profile
    
    if request.method == 'POST':
        # Handle profile updates
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        email = request.POST.get('email', '')
        
        # Update user info
        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()
        
        messages.success(request, 'Profile updated successfully.')
        return redirect('core:super_owner_profile')
    
    context = {
        'super_owner_profile': super_owner_profile,
        'user': request.user,
        'delegated_companies': super_owner_profile.delegated_companies.all() if hasattr(super_owner_profile, 'delegated_companies') else [],
        'permissions': {
            'can_activate_accounts': super_owner_profile.can_activate_accounts,
            'can_manage_companies': super_owner_profile.can_manage_companies,
            'can_delegate_permissions': super_owner_profile.can_delegate_permissions,
            'can_manage_billing': super_owner_profile.can_manage_billing,
            'can_view_system_analytics': super_owner_profile.can_view_system_analytics,
            'can_access_django_admin': super_owner_profile.can_access_django_admin,
        }
    }
    
    return render(request, 'admin/super_owner/profile.html', context)


@login_required
@user_passes_test(is_super_owner, login_url='/admin/login/')
def system_management(request):
    """System management tools and utilities"""
    context = {
        'django_admin_url': '/admin/',
        'super_owner_profile': request.user.super_owner_profile,
    }
    
    return render(request, 'admin/super_owner/system_management.html', context)


@login_required
@user_passes_test(is_super_owner, login_url='/admin/login/')
def super_owner_notifications(request):
    """Super Owner system notifications and alerts"""
    from .models import Notification
    
    # Get system-level notifications for super owners
    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')
    
    # Mark as read if requested
    if request.method == 'POST':
        notification_id = request.POST.get('mark_read')
        if notification_id:
            try:
                notification = notifications.get(id=notification_id)
                notification.mark_as_read()
                return JsonResponse({'success': True})
            except Notification.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Notification not found'})
    
    # Get system statistics for notifications
    system_alerts = {
        'pending_registrations': AccountActivationRequest.objects.filter(status='pending').count(),
        'failed_backups': 0,  # Would be implemented with actual backup monitoring
        'system_errors': 0,   # Would be implemented with error logging
        'maintenance_due': False,  # Would be implemented with maintenance scheduling
    }
    
    context = {
        'notifications': notifications,
        'system_alerts': system_alerts,
        'unread_count': notifications.filter(read_at__isnull=True).count(),
        'super_owner_profile': request.user.super_owner_profile,
    }
    
    return render(request, 'admin/super_owner/notifications.html', context)


@login_required
@user_passes_test(is_super_owner, login_url='/admin/login/')
def super_owner_backup_management(request):
    """Super Owner Backup Management - calls the regular backup view with super owner context"""
    from .backup_views import backup_management
    
    # Call the regular backup management view, which will detect super owner context
    return backup_management(request)


@login_required
@user_passes_test(is_super_owner, login_url='/admin/login/')
def debug_session(request):
    """Debug view for super owners to check session/login issues"""
    from django.contrib.sessions.models import Session
    from django.utils import timezone
    
    # Get current session info
    session_key = request.session.session_key
    session_data = dict(request.session)
    
    # Check user info
    user_info = {
        'username': request.user.username,
        'id': request.user.id,
        'is_authenticated': request.user.is_authenticated,
        'is_active': request.user.is_active,
        'is_staff': request.user.is_staff,
        'is_superuser': request.user.is_superuser,
    }
    
    # Check profile info
    profile_info = {}
    try:
        profile = request.user.userprofile
        profile_info = {
            'account_type': profile.account_type,
            'is_account_active': profile.is_account_active,
            'is_super_owner': profile.is_super_owner(),
            'last_company': str(profile.last_company) if profile.last_company else None,
        }
    except Exception as e:
        profile_info['error'] = str(e)
    
    # Check super owner info
    super_owner_info = {}
    try:
        super_owner = request.user.super_owner_profile
        super_owner_info = {
            'is_primary_owner': super_owner.is_primary_owner,
            'delegation_level': super_owner.delegation_level,
            'can_activate_accounts': super_owner.can_activate_accounts,
            'can_manage_companies': super_owner.can_manage_companies,
        }
    except Exception as e:
        super_owner_info['error'] = str(e)
    
    # Check active sessions for this user
    active_sessions = Session.objects.filter(expire_date__gt=timezone.now())
    user_sessions = []
    for session in active_sessions:
        data = session.get_decoded()
        if str(request.user.id) == str(data.get('_auth_user_id')):
            user_sessions.append({
                'session_key': session.session_key[:10] + '...',
                'expire_date': session.expire_date,
            })
    
    # Clear session action
    if request.method == 'POST' and 'clear_sessions' in request.POST:
        for session in active_sessions:
            data = session.get_decoded()
            if str(request.user.id) == str(data.get('_auth_user_id')):
                session.delete()
        messages.success(request, 'All your sessions have been cleared. Please login again.')
        return redirect('/login/')
    
    context = {
        'session_key': session_key,
        'session_data': session_data,
        'user_info': user_info,
        'profile_info': profile_info,
        'super_owner_info': super_owner_info,
        'user_sessions': user_sessions,
        'request_path': request.path,
        'request_method': request.method,
    }
    
    return render(request, 'admin/super_owner/debug_session.html', context)
