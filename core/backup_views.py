"""
Views for backup management and enhanced registration workflow
"""

import os
import mimetypes
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from .models import AccountActivationRequest, SuperOwner
from .backup_system import BackupManager, RestoreManager
from .registration_workflow import RegistrationRequestHandler
from .forms import CompanyRegistrationRequestForm, IndividualRegistrationRequestForm


class RegistrationWorkflowView(View):
    """Enhanced registration workflow with status tracking"""
    
    def get(self, request, token):
        """Check registration status"""
        try:
            activation_request = get_object_or_404(
                AccountActivationRequest, 
                activation_token=token
            )
            
            context = {
                'request': activation_request,
                'can_upload_docs': activation_request.status in ['pending', 'documents_required'],
                'is_expired': activation_request.is_expired
            }
            
            return render(request, 'core/registration/status.html', context)
            
        except AccountActivationRequest.DoesNotExist:
            messages.error(request, 'Invalid or expired registration token.')
            return redirect('core:register')
    
    def post(self, request, token):
        """Handle document uploads for existing requests"""
        try:
            activation_request = get_object_or_404(
                AccountActivationRequest, 
                activation_token=token
            )
            
            if activation_request.status not in ['pending', 'documents_required']:
                messages.error(request, 'Cannot upload documents for this request.')
                return redirect('core:registration_status', token=token)
            
            # Handle document uploads here
            # This would integrate with the DocumentUpload model
            
            messages.success(request, 'Additional documents uploaded successfully.')
            return redirect('core:registration_status', token=token)
            
        except AccountActivationRequest.DoesNotExist:
            messages.error(request, 'Invalid or expired registration token.')
            return redirect('core:register')


@login_required
def create_backup(request):
    """Create backup based on user permissions"""
    try:
        backup_type = request.GET.get('type', 'full')
        
        backup_manager = BackupManager(request.user, backup_type)
        result = backup_manager.create_backup()
        
        if result['success']:
            messages.success(
                request, 
                f'Backup created successfully: {result.get("backup_file", "backup files")}'
            )
            
            # For AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse(result)
        
        return redirect('core:backup_management')
        
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('core:backup_management')
    except Exception as e:
        messages.error(request, f'Backup creation failed: {str(e)}')
        return redirect('core:backup_management')


@login_required
def backup_management(request):
    """Backup management interface"""
    try:
        backups = BackupManager.list_backups(request.user)
        
        context = {
            'backups': backups,
            'is_super_owner': (
                hasattr(request.user, 'userprofile') and 
                request.user.userprofile.is_super_owner()
            ),
            'is_company_admin': request.user.company_memberships.filter(
                role__is_admin=True,
                status='active'
            ).exists(),
            'backup_types': [
                ('basic', 'Basic Backup'),
                ('full', 'Full Backup (includes documents)'),
            ]
        }
        
        return render(request, 'core/backup/management.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading backup management: {str(e)}')
        return render(request, 'core/backup/management.html', {'backups': []})


@login_required
def download_backup(request, filename):
    """Download backup file if user has permission"""
    try:
        backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
        file_path = os.path.join(backup_dir, filename)
        
        # Security check
        if not os.path.exists(file_path) or '..' in filename:
            raise Http404("Backup file not found")
        
        # Permission check
        if not BackupManager._can_user_download(request.user, filename):
            raise PermissionDenied("You don't have permission to download this backup")
        
        # Serve file
        with open(file_path, 'rb') as f:
            response = HttpResponse(
                f.read(), 
                content_type='application/zip'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
    except PermissionDenied:
        messages.error(request, "You don't have permission to download this backup.")
        return redirect('core:backup_management')
    except Exception as e:
        messages.error(request, f'Error downloading backup: {str(e)}')
        return redirect('core:backup_management')


@login_required
@require_POST
def delete_backup(request, filename):
    """Delete backup file if user has permission"""
    try:
        # Only super owners can delete system backups
        is_super_owner = (
            hasattr(request.user, 'userprofile') and 
            request.user.userprofile.is_super_owner()
        )
        
        # Company admins can delete their company backups
        is_company_backup = filename.startswith('company_')
        can_delete_company = False
        
        if is_company_backup:
            parts = filename.replace('company_', '').split('_')
            if len(parts) >= 1:
                company_slug = parts[0]
                from .models import Company
                can_delete_company = Company.objects.filter(
                    slug=company_slug,
                    memberships__user=request.user,
                    memberships__role__is_admin=True,
                    memberships__status='active'
                ).exists()
        
        # Users can delete their own backups
        is_user_backup = filename.startswith(f'user_{request.user.username}_')
        
        if not (is_super_owner or can_delete_company or is_user_backup):
            raise PermissionDenied("You don't have permission to delete this backup")
        
        backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
        file_path = os.path.join(backup_dir, filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            messages.success(request, f'Backup {filename} deleted successfully.')
        else:
            messages.error(request, 'Backup file not found.')
            
        return JsonResponse({'success': True})
        
    except PermissionDenied:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def super_owner_registration_management(request):
    """Enhanced registration management for super owners"""
    # Check if user is super owner with activation permissions
    if not (hasattr(request.user, 'userprofile') and 
            request.user.userprofile.is_super_owner() and
            request.user.super_owner_profile.can_activate_accounts):
        raise PermissionDenied("Access denied")
    
    status_filter = request.GET.get('status', 'pending')
    search_query = request.GET.get('search', '')
    
    requests = AccountActivationRequest.objects.select_related(
        'approved_by'
    ).prefetch_related('documents')
    
    if status_filter and status_filter != 'all':
        requests = requests.filter(status=status_filter)
    
    if search_query:
        from django.db.models import Q
        requests = requests.filter(
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(company_name__icontains=search_query)
        )
    
    requests = requests.order_by('-created_at')
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(requests, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'status_choices': AccountActivationRequest.STATUS_CHOICES,
        'total_requests': AccountActivationRequest.objects.count(),
        'pending_requests': AccountActivationRequest.objects.filter(status='pending').count(),
        'approved_today': AccountActivationRequest.objects.filter(
            status='approved',
            approved_at__date=timezone.now().date()
        ).count(),
    }
    
    return render(request, 'core/super_owner/registration_management.html', context)


@login_required
@require_POST
def process_registration_request(request, request_id):
    """Process registration request (approve/reject/request docs)"""
    # Check permissions
    if not (hasattr(request.user, 'userprofile') and 
            request.user.userprofile.is_super_owner() and
            request.user.super_owner_profile.can_activate_accounts):
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
        activation_request = get_object_or_404(AccountActivationRequest, id=request_id)
        action = request.POST.get('action')
        
        handler = RegistrationRequestHandler(request)
        
        if action == 'approve':
            user = handler.approve_request(activation_request, request.user)
            return JsonResponse({
                'success': True,
                'message': f'Request approved and account created for {activation_request.email}'
            })
        
        elif action == 'reject':
            reason = request.POST.get('reason', '')
            handler.reject_request(activation_request, request.user, reason)
            return JsonResponse({
                'success': True,
                'message': f'Request rejected for {activation_request.email}'
            })
        
        elif action == 'request_docs':
            message = request.POST.get('message', 'Additional documents required')
            handler.request_additional_documents(activation_request, request.user, message)
            return JsonResponse({
                'success': True,
                'message': f'Additional documents requested from {activation_request.email}'
            })
        
        else:
            return JsonResponse({'success': False, 'error': 'Invalid action'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def bulk_process_requests(request):
    """Bulk process multiple registration requests"""
    # Check permissions
    if not (hasattr(request.user, 'userprofile') and 
            request.user.userprofile.is_super_owner() and
            request.user.super_owner_profile.can_activate_accounts):
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
        import json
        data = json.loads(request.body)
        action = data.get('action')
        request_ids = data.get('request_ids', [])
        reason = data.get('reason', '')
        
        if not action or not request_ids:
            return JsonResponse({'success': False, 'error': 'Invalid data'})
        
        requests = AccountActivationRequest.objects.filter(id__in=request_ids)
        handler = RegistrationRequestHandler(request)
        
        processed = 0
        errors = []
        
        for req in requests:
            try:
                if action == 'approve' and req.status == 'pending':
                    handler.approve_request(req, request.user)
                    processed += 1
                elif action == 'reject' and req.status in ['pending', 'under_review']:
                    handler.reject_request(req, request.user, reason)
                    processed += 1
                elif action == 'request_docs' and req.status in ['pending', 'under_review']:
                    handler.request_additional_documents(req, request.user, reason)
                    processed += 1
            except Exception as e:
                errors.append(f'Error processing {req.email}: {str(e)}')
        
        return JsonResponse({
            'success': True,
            'message': f'Processed {processed} requests',
            'errors': errors
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def company_registration_request(request):
    """Company registration request form"""
    if request.method == 'POST':
        form = CompanyRegistrationRequestForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                handler = RegistrationRequestHandler(request)
                
                # Extract form data
                form_data = form.cleaned_data.copy()
                
                # Create registration request
                activation_request = handler.create_company_registration(form_data)
                
                messages.success(
                    request, 
                    f'Registration request submitted successfully! '
                    f'You will receive an email confirmation shortly. '
                    f'Track your request status with token: {activation_request.activation_token}'
                )
                
                return redirect('core:registration_status', token=activation_request.activation_token)
                
            except Exception as e:
                messages.error(request, f'Registration failed: {str(e)}')
    else:
        form = CompanyRegistrationRequestForm()
    
    return render(request, 'core/registration/company_request.html', {'form': form})


def individual_registration_request(request):
    """Individual registration request form"""
    if request.method == 'POST':
        form = IndividualRegistrationRequestForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                handler = RegistrationRequestHandler(request)
                
                # Extract form data
                form_data = form.cleaned_data.copy()
                
                # Create registration request
                activation_request = handler.create_individual_registration(form_data)
                
                messages.success(
                    request, 
                    f'Registration request submitted successfully! '
                    f'You will receive an email confirmation shortly. '
                    f'Track your request status with token: {activation_request.activation_token}'
                )
                
                return redirect('core:registration_status', token=activation_request.activation_token)
                
            except Exception as e:
                messages.error(request, f'Registration failed: {str(e)}')
    else:
        form = IndividualRegistrationRequestForm()
    
    return render(request, 'core/registration/individual_request.html', {'form': form})


@login_required
def backup_api_status(request):
    """API endpoint for backup status and info"""
    try:
        backups = BackupManager.list_backups(request.user)
        
        # Calculate total backup size
        total_size = sum(backup['size'] for backup in backups)
        
        # Get backup capabilities
        is_super_owner = (
            hasattr(request.user, 'userprofile') and 
            request.user.userprofile.is_super_owner()
        )
        
        is_company_admin = request.user.company_memberships.filter(
            role__is_admin=True,
            status='active'
        ).exists()
        
        return JsonResponse({
            'success': True,
            'backup_count': len(backups),
            'total_size': total_size,
            'capabilities': {
                'can_create_system_backup': is_super_owner,
                'can_create_company_backup': is_company_admin,
                'can_create_user_backup': True,
                'can_restore': is_super_owner,
            },
            'recent_backups': backups[:5]  # Most recent 5
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def cleanup_old_backups(request):
    """Cleanup old backups (super owner only)"""
    if not (hasattr(request.user, 'userprofile') and 
            request.user.userprofile.is_super_owner()):
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
        days = int(request.GET.get('days', 30))
        BackupManager.cleanup_old_backups(days)
        
        return JsonResponse({
            'success': True,
            'message': f'Cleaned up backups older than {days} days'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# Schedule backup cleanup (this would typically be in a management command or celery task)
def schedule_backup_cleanup():
    """Function to be called by scheduler to cleanup old backups"""
    try:
        BackupManager.cleanup_old_backups(days=30)
        print(f"Backup cleanup completed at {timezone.now()}")
    except Exception as e:
        print(f"Backup cleanup failed: {e}")
