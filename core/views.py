from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.urls import reverse
from django.http import JsonResponse, HttpResponse, Http404
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.utils.text import slugify
from django.template.loader import render_to_string
import secrets
from .models import (
    Company, CompanyMembership, Role, Notification, UserProfile,
    AccountActivationRequest, DocumentUpload, SuperOwner
)
from .forms import (
    CompanyRegistrationForm, RoleForm, UserInviteForm, UserProfileForm,
    FlexibleAuthenticationForm, CompanyRegistrationRequestForm,
    IndividualRegistrationRequestForm
)

def login_view(request):
    """Enhanced user login view with email/username support"""
    if request.user.is_authenticated:
        # Check if user is a super owner - redirect to super owner dashboard
        try:
            if hasattr(request.user, 'userprofile') and request.user.userprofile.is_super_owner():
                return redirect('/super-owner/')
        except:
            pass
        return redirect('dashboard:dashboard')
    
    if request.method == 'POST':
        form = FlexibleAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # Check if user account is active and approved (skip for super owners)
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            # Super owners bypass account activation checks
            is_super_owner = profile.is_super_owner()
            
            if not profile.is_account_active and not is_super_owner:
                messages.error(request, 'Your account is pending approval. Please wait for activation.')
                return render(request, 'registration/login.html', {'form': form})
            
            login(request, user)
            
            # Check for pending invitation
            if 'invitation_token' in request.session:
                token = request.session.pop('invitation_token')
                try:
                    membership = CompanyMembership.objects.get(
                        invitation_token=token,
                        status='invited'
                    )
                    membership.user = user
                    membership.status = 'active'
                    membership.joined_date = timezone.now()
                    membership.save()
                    messages.success(request, f'Welcome to {membership.company.name}!')
                except CompanyMembership.DoesNotExist:
                    pass
            
            # Super owners get redirected to their dashboard
            if is_super_owner:
                return redirect('/super-owner/')
            
            return redirect(request.GET.get('next', 'dashboard:dashboard'))
    else:
        form = FlexibleAuthenticationForm()
    
    return render(request, 'registration/login.html', {'form': form})

def register_view(request):
    """Registration selection view - choose between company or individual registration"""
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')
    
    return render(request, 'registration/register_selection.html')

def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('core:login')

@login_required
def profile_view(request):
    """User profile view"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    current_company = get_current_company(request)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('core:profile')
    else:
        form = UserProfileForm(instance=profile)
    
    memberships = CompanyMembership.objects.filter(
        user=request.user,
        status='active'
    )
    
    return render(request, 'core/profile.html', {
        'form': form,
        'profile': profile,
        'current_company': current_company,
        'memberships': memberships
    })

def company_register(request):
    """Company registration for SaaS onboarding"""
    if request.method == 'POST':
        form = CompanyRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    company = form.save()
                    # Login the admin user
                    admin_user = User.objects.get(email=form.cleaned_data['admin_email'])
                    login(request, admin_user)
                    
                    messages.success(request, 
                        f'Welcome to Construction Tracker! Your company "{company.name}" has been registered successfully.')
                    return redirect('dashboard:dashboard')
            except Exception as e:
                messages.error(request, f'Registration failed: {str(e)}')
    else:
        form = CompanyRegistrationForm()
    
    return render(request, 'core/company_register.html', {'form': form})

@login_required
def get_current_company(request):
    """Get user's current active company"""
    try:
        profile = request.user.userprofile
        if profile.last_company:
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

@login_required
def switch_company(request, company_id):
    """Switch user's active company"""
    try:
        company = get_object_or_404(Company, id=company_id)
        membership = CompanyMembership.objects.get(
            user=request.user,
            company=company,
            status='active'
        )
        
        # Update user's last company
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        profile.last_company = company
        profile.save()
        
        messages.success(request, f'Switched to {company.name}')
    except (Company.DoesNotExist, CompanyMembership.DoesNotExist):
        messages.error(request, 'You do not have access to this company')
    
    return redirect('dashboard:dashboard')

@login_required
def company_management(request):
    """Company management dashboard for admins"""
    current_company = get_current_company(request)
    if not current_company:
        messages.error(request, 'No company selected')
        return redirect('dashboard:dashboard')
    
    # Check if user is admin
    membership = CompanyMembership.objects.get(
        user=request.user, 
        company=current_company
    )
    if not membership.is_company_admin():
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard:dashboard')
    
    roles = current_company.roles.all()
    members = current_company.memberships.filter(status='active')
    
    context = {
        'company': current_company,
        'roles': roles,
        'members': members,
        'membership': membership
    }
    return render(request, 'core/company_management.html', context)

@login_required
def role_create(request):
    """Create a new role"""
    current_company = get_current_company(request)
    if not current_company:
        messages.error(request, 'No company selected')
        return redirect('dashboard:dashboard')
    
    # Check if user is admin
    membership = CompanyMembership.objects.get(
        user=request.user, 
        company=current_company
    )
    if not membership.is_company_admin():
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard:dashboard')
    
    if request.method == 'POST':
        form = RoleForm(request.POST, company=current_company)
        if form.is_valid():
            role = form.save()
            messages.success(request, f'Role "{role.name}" created successfully')
            return redirect('core:company_management')
    else:
        form = RoleForm(company=current_company)
    
    return render(request, 'core/role_form.html', {
        'form': form, 
        'title': 'Create Role',
        'company': current_company
    })

@login_required
def role_edit(request, role_id):
    """Edit an existing role"""
    current_company = get_current_company(request)
    if not current_company:
        messages.error(request, 'No company selected')
        return redirect('dashboard:dashboard')
    
    # Check if user is admin
    membership = CompanyMembership.objects.get(
        user=request.user, 
        company=current_company
    )
    if not membership.is_company_admin():
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard:dashboard')
    
    role = get_object_or_404(Role, id=role_id, company=current_company)
    
    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role, company=current_company)
        if form.is_valid():
            role = form.save()
            messages.success(request, f'Role "{role.name}" updated successfully')
            return redirect('core:company_management')
    else:
        form = RoleForm(instance=role, company=current_company)
    
    return render(request, 'core/role_form.html', {
        'form': form, 
        'title': 'Edit Role',
        'role': role,
        'company': current_company
    })

@login_required
def role_delete(request, role_id):
    """Delete a role"""
    current_company = get_current_company(request)
    if not current_company:
        messages.error(request, 'No company selected')
        return redirect('dashboard:dashboard')
    
    # Check if user is admin
    membership = CompanyMembership.objects.get(
        user=request.user, 
        company=current_company
    )
    if not membership.is_company_admin():
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard:dashboard')
    
    role = get_object_or_404(Role, id=role_id, company=current_company)
    
    # Check if role is being used by any members
    members_with_role = CompanyMembership.objects.filter(
        company=current_company, 
        role=role,
        status='active'
    ).count()
    
    if members_with_role > 0:
        messages.error(request, f'Cannot delete role "{role.name}" because it is assigned to {members_with_role} member(s). Please reassign these members to different roles first.')
        return redirect('core:user_management')
    
    # Prevent deletion of default admin roles
    if role.is_admin and current_company.roles.filter(is_admin=True).count() <= 1:
        messages.error(request, 'Cannot delete the last admin role. At least one admin role must exist.')
        return redirect('core:user_management')
    
    if request.method == 'POST':
        role_name = role.name
        role.delete()
        messages.success(request, f'Role "{role_name}" has been deleted successfully.')
        return redirect('core:user_management')
    
    return render(request, 'core/role_confirm_delete.html', {
        'role': role,
        'company': current_company,
        'members_count': members_with_role
    })

@login_required
def invite_user(request):
    """Enhanced user invitation for approved companies"""
    current_company = get_current_company(request)
    if not current_company:
        messages.error(request, 'No company selected')
        return redirect('dashboard:dashboard')
    
    # Check if user is admin or supervisor
    membership = CompanyMembership.objects.get(
        user=request.user, 
        company=current_company
    )
    if not (membership.is_company_admin() or membership.is_company_supervisor()):
        messages.error(request, 'Access denied. Admin or supervisor privileges required.')
        return redirect('dashboard:dashboard')
    
    # Check if company owner's account is approved
    if not _is_company_approved(current_company):
        messages.error(request, 'Company registration must be approved before inviting users.')
        return redirect('core:company_management')
    
    if request.method == 'POST':
        form = UserInviteForm(request.POST, company=current_company)
        if form.is_valid():
            email = form.cleaned_data['email']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            username = form.cleaned_data.get('username') or email
            role = form.cleaned_data['role']
            send_credentials = form.cleaned_data.get('send_credentials', True)
            message = form.cleaned_data.get('message', '')
            
            # Check if user already exists
            try:
                invited_user = User.objects.get(email=email)
                
                # Check if user's profile is activated (skip for super owners)
                profile, created = UserProfile.objects.get_or_create(user=invited_user)
                if not profile.is_account_active and not profile.is_super_owner():
                    messages.error(request, f'User {email} exists but account is not activated yet.')
                    return render(request, 'core/invite_user.html', {'form': form, 'company': current_company})
                
                # User exists and is activated, create membership directly
                membership_created = CompanyMembership.objects.create(
                    user=invited_user,
                    company=current_company,
                    role=role,
                    status='active',
                    invited_by=request.user,
                    joined_date=timezone.now()
                )
                
                # Send invitation notification
                _send_existing_user_invitation_email(invited_user, current_company, role, request.user, message)
                messages.success(request, f'User {email} has been added to the company')
                
            except User.DoesNotExist:
                # User doesn't exist, create new user account
                generated_password = User.objects.make_random_password(length=12)
                
                with transaction.atomic():
                    # Create the user
                    new_user = User.objects.create_user(
                        username=username,
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        password=generated_password
                    )
                    
                    # Create user profile (auto-approved for company invitations)
                    UserProfile.objects.create(
                        user=new_user,
                        last_company=current_company,
                        account_type='individual',
                        is_verified=True,
                        is_account_active=True,  # Auto-approve invited users
                        activated_by=request.user,
                        activated_at=timezone.now()
                    )
                    
                    # Create company membership
                    CompanyMembership.objects.create(
                        user=new_user,
                        company=current_company,
                        role=role,
                        status='active',
                        invited_by=request.user,
                        joined_date=timezone.now()
                    )
                
                # Send welcome email with credentials
                if send_credentials:
                    _send_new_user_invitation_email(new_user, generated_password, current_company, role, request.user, message)
                    messages.success(request, f'User account created for {email} and login credentials sent via email')
                else:
                    messages.success(request, f'User account created for {email} (credentials not sent via email)')
            
            return redirect('core:company_management')
    else:
        form = UserInviteForm(company=current_company)
    
    return render(request, 'core/invite_user.html', {
        'form': form,
        'company': current_company
    })

def accept_invitation(request, token):
    """Accept company invitation"""
    try:
        membership = CompanyMembership.objects.get(
            invitation_token=token,
            status='invited'
        )
        
        if request.user.is_authenticated:
            # User is logged in, accept invitation
            membership.user = request.user
            membership.status = 'active'
            membership.joined_date = timezone.now()
            membership.save()
            
            messages.success(request, f'Welcome to {membership.company.name}!')
            return redirect('dashboard:dashboard')
        else:
            # User needs to login or register
            request.session['invitation_token'] = token
            messages.info(request, 'Please login or create an account to accept the invitation')
            return redirect('core:login')
            
    except CompanyMembership.DoesNotExist:
        messages.error(request, 'Invalid or expired invitation')
        return redirect('core:login')

@login_required
def notifications(request):
    """View user notifications"""
    current_company = get_current_company(request)
    if not current_company:
        user_notifications = request.user.notifications.all()[:50]
    else:
        user_notifications = request.user.notifications.filter(
            company=current_company
        )[:50]
    
    return render(request, 'core/notifications.html', {
        'notifications': user_notifications,
        'company': current_company
    })

@login_required
def mark_notification_read(request, notification_id):
    """Mark notification as read"""
    notification = get_object_or_404(
        Notification, 
        id=notification_id, 
        recipient=request.user
    )
    notification.mark_as_read()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    return redirect('core:notifications')

@login_required
def notification_preferences(request):
    """Manage user notification preferences"""
    from .models import NotificationTemplate, UserNotificationPreference
    
    current_company = get_current_company(request)
    if not current_company:
        messages.error(request, 'No company selected')
        return redirect('dashboard:dashboard')
    
    # Get all notification templates for this company
    templates = NotificationTemplate.objects.filter(
        company=current_company,
        is_active=True
    ).order_by('name')
    
    preferences = []
    for template in templates:
        # Get or create user preference
        pref, created = UserNotificationPreference.objects.get_or_create(
            user=request.user,
            company=current_company,
            notification_template=template,
            defaults={
                'in_app_enabled': template.default_in_app,
                'email_enabled': template.default_email,
                'sms_enabled': template.default_sms,
                'is_enabled': True,
            }
        )
        preferences.append(pref)
    
    return render(request, 'core/notification_preferences.html', {
        'preferences': preferences,
        'company': current_company
    })

@login_required
def update_notification_preference(request):
    """AJAX endpoint to update notification preference"""
    import json
    from .models import UserNotificationPreference
    
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'})
    
    try:
        data = json.loads(request.body)
        preference_id = data.get('preference_id')
        preference_type = data.get('type')
        enabled = data.get('enabled', False)
        
        preference = get_object_or_404(
            UserNotificationPreference,
            id=preference_id,
            user=request.user
        )
        
        # Check if user can modify this preference
        if not preference.can_user_modify():
            return JsonResponse({
                'status': 'error', 
                'message': 'You do not have permission to modify this notification'
            })
        
        # Update the specific preference type
        if preference_type == 'in_app':
            preference.in_app_enabled = enabled
        elif preference_type == 'email':
            preference.email_enabled = enabled
        elif preference_type == 'sms':
            preference.sms_enabled = enabled
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid preference type'})
        
        preference.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Preference updated successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@login_required
def admin_notification_settings(request):
    """Admin view to manage company notification templates"""
    from .models import NotificationTemplate, CompanyMembership
    
    current_company = get_current_company(request)
    if not current_company:
        messages.error(request, 'No company selected')
        return redirect('dashboard:dashboard')
    
    # Check if user is admin
    try:
        membership = CompanyMembership.objects.get(
            user=request.user,
            company=current_company
        )
        if not membership.is_company_admin():
            messages.error(request, 'Admin access required')
            return redirect('dashboard:dashboard')
    except CompanyMembership.DoesNotExist:
        messages.error(request, 'You are not a member of this company')
        return redirect('dashboard:dashboard')
    
    if request.method == 'POST':
        # Handle form submission for updating notification templates
        template_id = request.POST.get('template_id')
        template = get_object_or_404(NotificationTemplate, id=template_id, company=current_company)
        
        # Update template settings
        template.control_level = request.POST.get('control_level', template.control_level)
        template.default_priority = request.POST.get('default_priority', template.default_priority)
        template.default_in_app = request.POST.get('default_in_app') == 'on'
        template.default_email = request.POST.get('default_email') == 'on'
        template.default_sms = request.POST.get('default_sms') == 'on'
        template.is_active = request.POST.get('is_active') == 'on'
        
        template.save()
        messages.success(request, f'Updated settings for {template.name}')
        return redirect('core:admin_notification_settings')
    
    templates = NotificationTemplate.objects.filter(
        company=current_company
    ).order_by('name')
    
    return render(request, 'core/admin_notification_settings.html', {
        'templates': templates,
        'company': current_company
    })

@login_required
def supervisor_dashboard(request):
    """Special dashboard for supervisors/executives with high-level overview"""
    current_company = get_current_company(request)
    if not current_company:
        messages.error(request, 'No company selected')
        return redirect('dashboard:dashboard')
    
    # Check if user is supervisor
    membership = CompanyMembership.objects.get(
        user=request.user, 
        company=current_company
    )
    if not membership.is_company_supervisor():
        messages.error(request, 'Access denied. Supervisor privileges required.')
        return redirect('dashboard:dashboard')
    
    # Get high-level metrics
    from projects.models import Project
    from expenses.models import Expense
    from decimal import Decimal
    
    projects = Project.objects.filter(company=current_company)
    expenses = Expense.objects.filter(project__company=current_company)
    
    context = {
        'company': current_company,
        'membership': membership,
        'total_projects': projects.count(),
        'active_projects': projects.filter(status='in_progress').count(),
        'completed_projects': projects.filter(status='completed').count(),
        'overdue_projects': [p for p in projects if p.is_overdue],
        'total_budget': sum(p.total_budget for p in projects),
        'total_spent': sum(e.actual_cost for e in expenses),
        'pending_expenses': expenses.filter(status='planned').count(),
        'recent_notifications': request.user.notifications.filter(
            company=current_company
        )[:10]
    }
    
    return render(request, 'core/supervisor_dashboard.html', context)

@login_required
def reports_view(request):
    """Reports and analytics view"""
    current_company = get_current_company(request)
    if not current_company:
        messages.error(request, 'No company selected')
        return redirect('dashboard:dashboard')
    
    from projects.models import Project
    from expenses.models import Expense
    from decimal import Decimal
    from django.db.models import Sum, Count
    from django.utils import timezone
    from datetime import datetime, timedelta
    
    # Get data for reports
    projects = Project.objects.filter(company=current_company)
    expenses = Expense.objects.filter(project__company=current_company)
    
    # Monthly data for charts
    monthly_data = []
    for i in range(12):
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30*i)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        monthly_expenses = expenses.filter(
            expense_date__range=[month_start, month_end]
        ).aggregate(total=Sum('actual_cost'))['total'] or 0
        
        monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'expenses': float(monthly_expenses)
        })
    
    context = {
        'company': current_company,
        'total_projects': projects.count(),
        'total_expenses': expenses.aggregate(total=Sum('actual_cost'))['total'] or 0,
        'total_budget': projects.aggregate(total=Sum('total_budget'))['total'] or 0,
        'monthly_data': monthly_data[::-1],  # Reverse to show chronologically
        'projects_by_status': projects.values('status').annotate(count=Count('id')),
    }
    
    return render(request, 'core/reports.html', context)

@login_required
def quarterly_summary_view(request):
    """Quarterly summary view"""
    current_company = get_current_company(request)
    if not current_company:
        messages.error(request, 'No company selected')
        return redirect('dashboard:dashboard')
    
    from projects.models import Project
    from expenses.models import Expense
    from django.db.models import Sum
    from django.utils import timezone
    from datetime import datetime, timedelta
    import calendar
    
    # Get current quarter
    now = timezone.now()
    current_quarter = (now.month - 1) // 3 + 1
    quarter_start = datetime(now.year, 3 * current_quarter - 2, 1)
    quarter_end = datetime(now.year, 3 * current_quarter, calendar.monthrange(now.year, 3 * current_quarter)[1])
    
    projects = Project.objects.filter(company=current_company)
    expenses = Expense.objects.filter(
        project__company=current_company,
        expense_date__range=[quarter_start, quarter_end]
    )
    
    context = {
        'company': current_company,
        'quarter': current_quarter,
        'year': now.year,
        'quarter_start': quarter_start,
        'quarter_end': quarter_end,
        'quarter_expenses': expenses.aggregate(total=Sum('actual_cost'))['total'] or 0,
        'quarter_projects': projects.filter(created_at__range=[quarter_start, quarter_end]).count(),
        'completed_projects': projects.filter(status='completed', updated_at__range=[quarter_start, quarter_end]).count(),
    }
    
    return render(request, 'core/quarterly_summary.html', context)

# Registration and Approval Workflow Views

def company_registration_request(request):
    """Handle company registration requests with document upload"""
    if request.method == 'POST':
        form = CompanyRegistrationRequestForm(request.POST, request.FILES)
        if form.is_valid():
            activation_request = form.save()
            
            # Send notification to super owners
            _notify_super_owners_new_request(activation_request)
            
            messages.success(
                request,
                'Your company registration request has been submitted successfully. '
                'You will receive an email notification once your documents are reviewed.'
            )
            return redirect('core:registration_status', token=activation_request.activation_token)
    else:
        form = CompanyRegistrationRequestForm()
    
    return render(request, 'registration/company_registration_request.html', {'form': form})

def individual_registration_request(request):
    """Handle individual registration requests with document upload"""
    if request.method == 'POST':
        form = IndividualRegistrationRequestForm(request.POST, request.FILES)
        if form.is_valid():
            activation_request = form.save()
            
            # Send notification to super owners
            _notify_super_owners_new_request(activation_request)
            
            messages.success(
                request,
                'Your individual registration request has been submitted successfully. '
                'You will receive an email notification once your documents are reviewed.'
            )
            return redirect('core:registration_status', token=activation_request.activation_token)
    else:
        form = IndividualRegistrationRequestForm()
    
    return render(request, 'registration/individual_registration_request.html', {'form': form})

def registration_status(request, token):
    """Check registration status"""
    try:
        activation_request = AccountActivationRequest.objects.get(activation_token=token)
        documents = activation_request.documents.all().order_by('document_type')
        
        context = {
            'activation_request': activation_request,
            'documents': documents,
        }
        return render(request, 'registration/registration_status.html', context)
    except AccountActivationRequest.DoesNotExist:
        messages.error(request, 'Invalid or expired registration token.')
        return redirect('core:login')

# Super Owner Views for Approval Workflow

def is_super_owner(user):
    """Check if user is a super owner"""
    return (
        user.is_authenticated and 
        hasattr(user, 'userprofile') and 
        user.userprofile.is_super_owner()
    )

@login_required
@user_passes_test(is_super_owner)
def activation_requests_list(request):
    """List all activation requests for super owners"""
    status_filter = request.GET.get('status', 'pending')
    request_type_filter = request.GET.get('type', '')
    
    queryset = AccountActivationRequest.objects.all().order_by('-created_at')
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    if request_type_filter:
        queryset = queryset.filter(request_type=request_type_filter)
    
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    activation_requests = paginator.get_page(page_number)
    
    context = {
        'activation_requests': activation_requests,
        'status_filter': status_filter,
        'request_type_filter': request_type_filter,
        'status_choices': AccountActivationRequest.STATUS_CHOICES,
        'request_type_choices': AccountActivationRequest.REQUEST_TYPES,
    }
    return render(request, 'admin/activation_requests_list.html', context)

@login_required
@user_passes_test(is_super_owner)
def activation_request_detail(request, request_id):
    """View activation request details for review"""
    activation_request = get_object_or_404(AccountActivationRequest, id=request_id)
    documents = activation_request.documents.all().order_by('document_type')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        if action == 'approve':
            # Approve the request and create user/company
            try:
                with transaction.atomic():
                    _process_approval(activation_request, request.user)
                    messages.success(request, f'Registration request for {activation_request.email} has been approved.')
            except Exception as e:
                messages.error(request, f'Error processing approval: {str(e)}')
                
        elif action == 'reject':
            activation_request.reject(request.user, notes)
            _send_rejection_email(activation_request)
            messages.success(request, f'Registration request for {activation_request.email} has been rejected.')
            
        elif action == 'require_documents':
            activation_request.require_documents(request.user, notes)
            _send_documents_required_email(activation_request)
            messages.success(request, f'Additional documents requested from {activation_request.email}.')
            
        elif action == 'mark_review':
            activation_request.mark_under_review(request.user)
            messages.success(request, f'Request marked as under review.')
        
        return redirect('super_owner:activation_request_detail', request_id=request_id)
    
    context = {
        'activation_request': activation_request,
        'documents': documents,
    }
    return render(request, 'admin/activation_request_detail.html', context)

@login_required
@user_passes_test(is_super_owner)
def document_review(request, document_id):
    """Review individual documents"""
    document = get_object_or_404(DocumentUpload, id=document_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        if action == 'approve':
            document.approve(request.user, notes)
            messages.success(request, f'Document {document.get_document_type_display()} approved.')
        elif action == 'reject':
            document.reject(request.user, notes)
            messages.success(request, f'Document {document.get_document_type_display()} rejected.')
        elif action == 'require_revision':
            document.require_revision(request.user, notes)
            messages.success(request, f'Revision requested for {document.get_document_type_display()}.')
        
        return redirect('super_owner:activation_request_detail', request_id=document.activation_request.id)
    
    context = {
        'document': document,
        'activation_request': document.activation_request,
    }
    return render(request, 'admin/document_review.html', context)

def serve_document(request, document_id):
    """Serve protected document files"""
    document = get_object_or_404(DocumentUpload, id=document_id)
    
    # Check permissions - only super owners can view documents
    if not (request.user.is_authenticated and hasattr(request.user, 'super_owner_profile')):
        raise Http404("Document not found")
    
    try:
        response = HttpResponse(document.file.read())
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = f'inline; filename="{document.original_filename}"'
        return response
    except FileNotFoundError:
        raise Http404("Document file not found")

# Redirect Views for Legacy URLs

def redirect_to_super_owner_requests(request):
    """Redirect legacy admin requests URL to Super Owner dashboard"""
    return redirect('/super-owner/registration-requests/')

def redirect_to_super_owner_request_detail(request, request_id):
    """Redirect legacy admin request detail URL to Super Owner dashboard"""
    return redirect(f'/super-owner/registration-requests/{request_id}/')

# Helper Functions

def _notify_super_owners_new_request(activation_request):
    """Notify super owners about new registration request"""
    super_owners = SuperOwner.objects.filter(can_activate_accounts=True)
    
    for super_owner in super_owners:
        try:
            subject = f'New Registration Request - {activation_request.get_request_type_display()}'
            message = f"""
            A new registration request has been submitted:
            
            Type: {activation_request.get_request_type_display()}
            Name: {activation_request.first_name} {activation_request.last_name}
            Email: {activation_request.email}
            {'Company: ' + activation_request.company_name if activation_request.company_name else ''}
            
            Please review the request at: {settings.SITE_URL}/admin/activation-requests/{activation_request.id}/
            
            Documents have been uploaded and are ready for review.
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [super_owner.user.email],
                fail_silently=True,
            )
        except Exception:
            pass  # Continue if email fails

def _process_approval(activation_request, approver):
    """Process approval and create user/company accounts"""
    activation_request.approve(approver)
    
    if activation_request.request_type == 'company_registration':
        # Create company and admin user
        company = Company.objects.create(
            name=activation_request.company_name,
            slug=slugify(activation_request.company_name),
            description=activation_request.company_description,
            email=activation_request.email,
            phone=activation_request.phone,
            address=activation_request.company_address,
            website=activation_request.company_website or '',
        )
        
        # Create admin user with generated password
        generated_password = User.objects.make_random_password(length=12)
        admin_user = User.objects.create_user(
            username=activation_request.username,
            email=activation_request.email,
            first_name=activation_request.first_name,
            last_name=activation_request.last_name,
            password=generated_password
        )
        
        # Create user profile
        profile = UserProfile.objects.create(
            user=admin_user,
            phone=activation_request.phone,
            last_company=company,
            account_type='company',
            is_verified=True,
            documents_submitted=True,
            documents_verified=True,
            is_account_active=True,
            activated_by=approver,
            activated_at=timezone.now()
        )
        
        # Create default roles and company membership (use existing logic)
        _create_default_company_setup(company, admin_user)
        
        # Send welcome email with credentials
        _send_approval_email_company(activation_request, generated_password)
        
    elif activation_request.request_type == 'individual_registration':
        # Create individual user with generated password
        generated_password = User.objects.make_random_password(length=12)
        user = User.objects.create_user(
            username=activation_request.username,
            email=activation_request.email,
            first_name=activation_request.first_name,
            last_name=activation_request.last_name,
            password=generated_password
        )
        
        # Create user profile
        profile = UserProfile.objects.create(
            user=user,
            phone=activation_request.phone,
            account_type='individual',
            address=activation_request.metadata.get('address', ''),
            is_verified=True,
            documents_submitted=True,
            documents_verified=True,
            is_account_active=True,
            activated_by=approver,
            activated_at=timezone.now()
        )
        
        # Send welcome email
        _send_approval_email_individual(activation_request, generated_password)

def _create_default_company_setup(company, admin_user):
    """Create default roles and setup for approved company"""
    # Create admin role
    admin_role = Role.objects.create(
        company=company,
        name='Company Admin',
        description='Full access to all company features and settings',
        is_admin=True
    )
    
    # Create company membership
    CompanyMembership.objects.create(
        user=admin_user,
        company=company,
        role=admin_role,
        status='active',
        joined_date=timezone.now()
    )

def _send_approval_email_company(activation_request, password):
    """Send approval email to company admin"""
    subject = f'Company Registration Approved - {activation_request.company_name}'
    message = f"""
    Congratulations! Your company registration has been approved.
    
    Company: {activation_request.company_name}
    Admin Name: {activation_request.first_name} {activation_request.last_name}
    
    Your Login Credentials:
    Username: {activation_request.username}
    Password: {password}
    
    Login URL: {settings.SITE_URL}/login/
    
    Please change your password after first login.
    
    Welcome to ConstructPro!
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [activation_request.email],
        fail_silently=False,
    )

def _send_approval_email_individual(activation_request, password):
    """Send approval email to individual user"""
    subject = 'Individual Account Approved'
    message = f"""
    Congratulations! Your individual account registration has been approved.
    
    Name: {activation_request.first_name} {activation_request.last_name}
    
    Your Login Credentials:
    Username: {activation_request.username}
    Password: {password}
    
    Login URL: {settings.SITE_URL}/login/
    
    Please change your password after first login.
    
    Welcome to ConstructPro!
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [activation_request.email],
        fail_silently=False,
    )

def _send_rejection_email(activation_request):
    """Send rejection email"""
    subject = 'Registration Request Rejected'
    message = f"""
    We regret to inform you that your registration request has been rejected.
    
    Name: {activation_request.first_name} {activation_request.last_name}
    Email: {activation_request.email}
    
    Reason: {activation_request.rejection_reason}
    
    If you believe this is an error, please contact our support team.
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [activation_request.email],
        fail_silently=False,
    )

def _send_documents_required_email(activation_request):
    """Send email requesting additional documents"""
    subject = 'Additional Documents Required'
    message = f"""
    Additional documents are required for your registration request.
    
    Name: {activation_request.first_name} {activation_request.last_name}
    Email: {activation_request.email}
    
    Requirements: {activation_request.rejection_reason}
    
    Please check your registration status at: {settings.SITE_URL}/registration/status/{activation_request.activation_token}/
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [activation_request.email],
        fail_silently=False,
    )

# Helper Functions for User Management

def _is_company_approved(company):
    """Check if company has approved registration"""
    # Find company admin
    admin_membership = CompanyMembership.objects.filter(
        company=company,
        role__is_admin=True,
        status='active'
    ).first()
    
    if not admin_membership:
        return False
    
    # Check if admin's profile is activated (super owners bypass this check)
    try:
        profile = admin_membership.user.userprofile
        return profile.is_account_active or profile.is_super_owner()
    except UserProfile.DoesNotExist:
        return False

def _send_existing_user_invitation_email(user, company, role, inviter, custom_message=""):
    """Send invitation email to existing user"""
    subject = f'Invitation to join {company.name}'
    message = f"""
    Hello {user.first_name} {user.last_name},
    
    You have been invited to join {company.name} on ConstructPro.
    
    Role: {role.name}
    Invited by: {inviter.get_full_name() or inviter.username}
    
    {custom_message}
    
    You can login with your existing credentials at: {settings.SITE_URL}/login/
    
    Welcome to the team!
    
    Best regards,
    ConstructPro Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True,
        )
    except Exception:
        pass

def _send_new_user_invitation_email(user, password, company, role, inviter, custom_message=""):
    """Send welcome email with credentials to new user"""
    subject = f'Welcome to {company.name} on ConstructPro'
    message = f"""
    Hello {user.first_name} {user.last_name},
    
    Welcome to {company.name} on ConstructPro! Your account has been created.
    
    Your Login Credentials:
    Username: {user.username}
    Email: {user.email}
    Password: {password}
    
    Role: {role.name}
    Company: {company.name}
    Invited by: {inviter.get_full_name() or inviter.username}
    
    {custom_message}
    
    Login at: {settings.SITE_URL}/login/
    
    For security reasons, we recommend changing your password after your first login.
    
    Best regards,
    ConstructPro Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True,
        )
    except Exception:
        pass

# Super Owner Dashboard
@login_required
@user_passes_test(is_super_owner)
def super_owner_dashboard(request):
    """Super owner dashboard with system overview"""
    from django.utils import timezone
    from datetime import datetime, timedelta
    
    # Get statistics
    pending_requests = AccountActivationRequest.objects.filter(status='pending').count()
    under_review_requests = AccountActivationRequest.objects.filter(status='under_review').count()
    
    today = timezone.now().date()
    approved_today = AccountActivationRequest.objects.filter(
        status='approved',
        approved_at__date=today
    ).count()
    
    total_companies = Company.objects.filter(is_active=True).count()
    
    # Recent requests (last 10)
    recent_requests = AccountActivationRequest.objects.all().order_by('-created_at')[:10]
    
    context = {
        'pending_requests': pending_requests,
        'under_review_requests': under_review_requests,
        'approved_today': approved_today,
        'total_companies': total_companies,
        'recent_requests': recent_requests,
    }
    
    return render(request, 'admin/super_owner_dashboard.html', context)

@login_required
def company_settings_view(request):
    """Company settings view"""
    current_company = get_current_company(request)
    if not current_company:
        messages.error(request, 'No company selected')
        return redirect('dashboard:dashboard')
    
    # Check if user is admin
    membership = CompanyMembership.objects.get(
        user=request.user, 
        company=current_company
    )
    if not membership.is_company_admin():
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard:dashboard')
    
    if request.method == 'POST':
        form = CompanyRegistrationForm(request.POST, request.FILES, instance=current_company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Company settings updated successfully!')
            return redirect('core:company_settings')
    else:
        form = CompanyRegistrationForm(instance=current_company)
    
    context = {
        'form': form,
        'company': current_company,
        'user_membership': membership
    }
    
    return render(request, 'core/company_settings.html', context)

@login_required
def user_management_view(request):
    """User management dashboard for company admins"""
    current_company = get_current_company(request)
    if not current_company:
        messages.error(request, 'No company selected')
        return redirect('dashboard:dashboard')
    
    # Check if user is admin
    membership = CompanyMembership.objects.get(
        user=request.user, 
        company=current_company
    )
    if not membership.is_company_admin():
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('dashboard:dashboard')
    
    # Get all company members
    members = CompanyMembership.objects.filter(
        company=current_company
    ).select_related('user', 'role').order_by('-joined_date')
    
    # Get pending invitations
    pending_invitations = CompanyMembership.objects.filter(
        company=current_company,
        status='invited'
    )
    
    context = {
        'company': current_company,
        'members': members,
        'pending_invitations': pending_invitations,
        'total_members': members.filter(status='active').count(),
        'roles': current_company.roles.all()
    }
    
    return render(request, 'core/user_management.html', context)
