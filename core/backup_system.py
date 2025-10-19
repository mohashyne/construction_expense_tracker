"""
Comprehensive local backup system for Construction Tracker
Supports different backup levels based on user permissions
"""

import os
import json
import csv
import zipfile
import shutil
from datetime import datetime, timedelta
from django.conf import settings
from django.core.serializers import serialize
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db import models
from django.core.files.storage import default_storage
import logging

from .models import (
    Company, CompanyMembership, Role, Permission, UserProfile, 
    AccountActivationRequest, SuperOwner, Notification, DocumentUpload
)

logger = logging.getLogger(__name__)


class BackupManager:
    """Main backup manager class"""
    
    def __init__(self, user, backup_type='full'):
        self.user = user
        self.backup_type = backup_type
        self.backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Ensure backup directory exists
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def create_backup(self):
        """Create backup based on user permissions"""
        try:
            if self._is_super_owner():
                return self._create_super_owner_backup()
            elif self._is_company_admin():
                return self._create_company_backup()
            else:
                return self._create_user_backup()
        except Exception as e:
            logger.error(f"Backup creation failed for user {self.user.id}: {str(e)}")
            raise
    
    def _is_super_owner(self):
        """Check if user is a super owner"""
        return (
            hasattr(self.user, 'userprofile') and 
            self.user.userprofile.is_super_owner()
        )
    
    def _is_company_admin(self):
        """Check if user is a company admin"""
        return CompanyMembership.objects.filter(
            user=self.user,
            role__is_admin=True,
            status='active'
        ).exists()
    
    def _create_super_owner_backup(self):
        """Create comprehensive system backup for super owners"""
        backup_filename = f"system_backup_{self.timestamp}.zip"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # System metadata
            self._add_system_metadata(zipf)
            
            # All companies
            self._backup_all_companies(zipf)
            
            # All users
            self._backup_all_users(zipf)
            
            # Registration requests
            self._backup_registration_requests(zipf)
            
            # Super owners
            self._backup_super_owners(zipf)
            
            # System settings and configurations
            self._backup_system_settings(zipf)
            
            # Documents (if requested)
            if self.backup_type == 'full':
                self._backup_all_documents(zipf)
        
        return {
            'success': True,
            'backup_file': backup_filename,
            'backup_path': backup_path,
            'size': os.path.getsize(backup_path),
            'created_at': datetime.now().isoformat()
        }
    
    def _create_company_backup(self):
        """Create company-specific backup for company admins"""
        # Get user's companies where they are admin
        admin_companies = Company.objects.filter(
            memberships__user=self.user,
            memberships__role__is_admin=True,
            memberships__status='active'
        )
        
        if not admin_companies.exists():
            raise ValueError("User is not an admin of any company")
        
        # Create backup for each company
        backup_files = []
        
        for company in admin_companies:
            backup_filename = f"company_{company.slug}_{self.timestamp}.zip"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                self._backup_single_company(zipf, company)
            
            backup_files.append({
                'company': company.name,
                'filename': backup_filename,
                'path': backup_path,
                'size': os.path.getsize(backup_path)
            })
        
        return {
            'success': True,
            'backup_files': backup_files,
            'created_at': datetime.now().isoformat()
        }
    
    def _create_user_backup(self):
        """Create user-specific data backup"""
        backup_filename = f"user_{self.user.username}_{self.timestamp}.zip"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # User profile and data
            self._backup_user_data(zipf, self.user)
            
            # User's notifications
            self._backup_user_notifications(zipf, self.user)
        
        return {
            'success': True,
            'backup_file': backup_filename,
            'backup_path': backup_path,
            'size': os.path.getsize(backup_path),
            'created_at': datetime.now().isoformat()
        }
    
    def _add_system_metadata(self, zipf):
        """Add system metadata to backup"""
        metadata = {
            'backup_version': '1.0',
            'created_at': datetime.now().isoformat(),
            'created_by': self.user.username,
            'backup_type': self.backup_type,
            'django_version': getattr(settings, 'DJANGO_VERSION', 'unknown'),
            'total_users': User.objects.count(),
            'total_companies': Company.objects.count(),
            'total_requests': AccountActivationRequest.objects.count(),
        }
        
        zipf.writestr('metadata.json', json.dumps(metadata, indent=2))
    
    def _backup_all_companies(self, zipf):
        """Backup all companies and related data"""
        companies_data = []
        
        for company in Company.objects.all():
            company_data = {
                'id': str(company.id),
                'name': company.name,
                'slug': company.slug,
                'email': company.email,
                'description': company.description,
                'website': company.website,
                'address': company.address,
                'phone': company.phone,
                'is_active': company.is_active,
                'subscription_type': company.subscription_type,
                'created_at': company.created_at.isoformat(),
                'updated_at': company.updated_at.isoformat(),
            }
            
            # Company members
            members = []
            for membership in company.memberships.select_related('user', 'role'):
                members.append({
                    'user_id': membership.user.id,
                    'username': membership.user.username,
                    'email': membership.user.email,
                    'role': membership.role.name if membership.role else None,
                    'status': membership.status,
                    'joined_date': membership.joined_date.isoformat() if membership.joined_date else None,
                })
            company_data['members'] = members
            
            # Company roles
            roles = []
            for role in company.roles.all():
                role_data = {
                    'name': role.name,
                    'description': role.description,
                    'is_admin': role.is_admin,
                    'is_supervisor': role.is_supervisor,
                    'permissions': []
                }
                
                # Role permissions
                for perm in role.permissions.all():
                    role_data['permissions'].append({
                        'resource': perm.resource,
                        'action': perm.action
                    })
                
                roles.append(role_data)
            company_data['roles'] = roles
            
            companies_data.append(company_data)
        
        zipf.writestr('companies.json', json.dumps(companies_data, indent=2))
        
        # Also create CSV version
        self._create_companies_csv(zipf)
    
    def _backup_all_users(self, zipf):
        """Backup all users and profiles"""
        users_data = []
        
        for user in User.objects.select_related('userprofile'):
            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
            }
            
            # User profile
            if hasattr(user, 'userprofile'):
                profile = user.userprofile
                user_data['profile'] = {
                    'phone': profile.phone,
                    'account_type': profile.account_type,
                    'is_account_active': profile.is_account_active,
                    'is_verified': profile.is_verified,
                    'last_company': str(profile.last_company.id) if profile.last_company else None,
                    'activated_at': profile.activated_at.isoformat() if profile.activated_at else None,
                }
            
            users_data.append(user_data)
        
        zipf.writestr('users.json', json.dumps(users_data, indent=2))
        self._create_users_csv(zipf)
    
    def _backup_registration_requests(self, zipf):
        """Backup all registration requests"""
        requests_data = []
        
        for req in AccountActivationRequest.objects.select_related('approved_by'):
            request_data = {
                'id': str(req.id),
                'request_type': req.request_type,
                'status': req.status,
                'email': req.email,
                'username': req.username,
                'first_name': req.first_name,
                'last_name': req.last_name,
                'phone': req.phone,
                'company_name': req.company_name,
                'company_description': req.company_description,
                'company_website': req.company_website,
                'created_at': req.created_at.isoformat(),
                'approved_by': req.approved_by.username if req.approved_by else None,
                'approved_at': req.approved_at.isoformat() if req.approved_at else None,
                'rejection_reason': req.rejection_reason,
                'metadata': req.metadata,
            }
            requests_data.append(request_data)
        
        zipf.writestr('registration_requests.json', json.dumps(requests_data, indent=2))
        self._create_requests_csv(zipf)
    
    def _backup_super_owners(self, zipf):
        """Backup super owners configuration"""
        super_owners_data = []
        
        for so in SuperOwner.objects.select_related('user', 'created_by'):
            so_data = {
                'user_id': so.user.id,
                'username': so.user.username,
                'email': so.user.email,
                'is_primary_owner': so.is_primary_owner,
                'delegation_level': so.delegation_level,
                'permissions': {
                    'can_manage_companies': so.can_manage_companies,
                    'can_manage_users': so.can_manage_users,
                    'can_activate_accounts': so.can_activate_accounts,
                    'can_access_django_admin': so.can_access_django_admin,
                    'can_delegate_permissions': so.can_delegate_permissions,
                    'can_manage_billing': so.can_manage_billing,
                    'can_view_system_analytics': so.can_view_system_analytics,
                },
                'allowed_companies': [str(c.id) for c in so.allowed_companies.all()],
                'created_by': so.created_by.username if so.created_by else None,
                'created_at': so.created_at.isoformat(),
            }
            super_owners_data.append(so_data)
        
        zipf.writestr('super_owners.json', json.dumps(super_owners_data, indent=2))
    
    def _backup_system_settings(self, zipf):
        """Backup system settings and configuration"""
        settings_data = {
            'site_url': getattr(settings, 'SITE_URL', ''),
            'default_currency': getattr(settings, 'DEFAULT_CURRENCY', 'USD'),
            'email_backend': getattr(settings, 'EMAIL_BACKEND', ''),
            'debug': getattr(settings, 'DEBUG', False),
            'allowed_hosts': getattr(settings, 'ALLOWED_HOSTS', []),
            'installed_apps': getattr(settings, 'INSTALLED_APPS', []),
        }
        
        zipf.writestr('system_settings.json', json.dumps(settings_data, indent=2))
    
    def _backup_single_company(self, zipf, company):
        """Backup a single company's data"""
        # Company basic info
        company_data = {
            'id': str(company.id),
            'name': company.name,
            'slug': company.slug,
            'email': company.email,
            'description': company.description,
            'website': company.website,
            'address': company.address,
            'phone': company.phone,
            'is_active': company.is_active,
            'subscription_type': company.subscription_type,
            'created_at': company.created_at.isoformat(),
            'updated_at': company.updated_at.isoformat(),
        }
        
        zipf.writestr('company_info.json', json.dumps(company_data, indent=2))
        
        # Company members
        members_data = []
        for membership in company.memberships.select_related('user', 'role'):
            members_data.append({
                'user_id': membership.user.id,
                'username': membership.user.username,
                'email': membership.user.email,
                'first_name': membership.user.first_name,
                'last_name': membership.user.last_name,
                'role': membership.role.name if membership.role else None,
                'status': membership.status,
                'joined_date': membership.joined_date.isoformat() if membership.joined_date else None,
            })
        
        zipf.writestr('members.json', json.dumps(members_data, indent=2))
        
        # Company roles and permissions
        roles_data = []
        for role in company.roles.all():
            role_data = {
                'name': role.name,
                'description': role.description,
                'is_admin': role.is_admin,
                'is_supervisor': role.is_supervisor,
                'permissions': []
            }
            
            for perm in role.permissions.all():
                role_data['permissions'].append({
                    'resource': perm.resource,
                    'action': perm.action
                })
            
            roles_data.append(role_data)
        
        zipf.writestr('roles.json', json.dumps(roles_data, indent=2))
        
        # Try to backup related data from other apps if they exist
        self._backup_company_projects(zipf, company)
        self._backup_company_expenses(zipf, company)
        self._backup_company_contractors(zipf, company)
    
    def _backup_company_projects(self, zipf, company):
        """Backup company projects if projects app exists"""
        try:
            from projects.models import Project
            projects = Project.objects.filter(company=company)
            
            projects_data = []
            for project in projects:
                project_data = {
                    'name': project.name,
                    'description': project.description,
                    'status': project.status,
                    'start_date': project.start_date.isoformat() if project.start_date else None,
                    'expected_completion_date': project.expected_completion_date.isoformat() if project.expected_completion_date else None,
                    'actual_completion_date': project.actual_completion_date.isoformat() if project.actual_completion_date else None,
                    'total_budget': str(project.total_budget) if project.total_budget else None,
                    'created_at': project.created_at.isoformat(),
                }
                projects_data.append(project_data)
            
            zipf.writestr('projects.json', json.dumps(projects_data, indent=2))
        except ImportError:
            pass  # Projects app not installed
    
    def _backup_company_expenses(self, zipf, company):
        """Backup company expenses if expenses app exists"""
        try:
            from expenses.models import Expense
            expenses = Expense.objects.filter(project__company=company)
            
            expenses_data = []
            for expense in expenses:
                expense_data = {
                    'title': expense.title,
                    'description': expense.description,
                    'planned_cost': str(expense.planned_cost) if expense.planned_cost else None,
                    'actual_cost': str(expense.actual_cost) if expense.actual_cost else None,
                    'expense_date': expense.expense_date.isoformat() if expense.expense_date else None,
                    'category': expense.category.name if expense.category else None,
                    'project': expense.project.name if expense.project else None,
                    'created_at': expense.created_at.isoformat(),
                }
                expenses_data.append(expense_data)
            
            zipf.writestr('expenses.json', json.dumps(expenses_data, indent=2))
        except ImportError:
            pass  # Expenses app not installed
    
    def _backup_company_contractors(self, zipf, company):
        """Backup company contractors if contractors app exists"""
        try:
            from contractors.models import Contractor
            contractors = Contractor.objects.filter(company=company)
            
            contractors_data = []
            for contractor in contractors:
                contractor_data = {
                    'name': contractor.name,
                    'email': contractor.email,
                    'phone': contractor.phone,
                    'address': contractor.address,
                    'specialization': contractor.specialization,
                    'rating': contractor.rating,
                    'is_active': contractor.is_active,
                    'created_at': contractor.created_at.isoformat(),
                }
                contractors_data.append(contractor_data)
            
            zipf.writestr('contractors.json', json.dumps(contractors_data, indent=2))
        except ImportError:
            pass  # Contractors app not installed
    
    def _backup_user_data(self, zipf, user):
        """Backup user-specific data"""
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
        }
        
        # User profile
        if hasattr(user, 'userprofile'):
            profile = user.userprofile
            user_data['profile'] = {
                'phone': profile.phone,
                'account_type': profile.account_type,
                'is_account_active': profile.is_account_active,
                'is_verified': profile.is_verified,
            }
        
        # User's company memberships
        memberships = []
        for membership in user.company_memberships.select_related('company', 'role'):
            memberships.append({
                'company': membership.company.name,
                'role': membership.role.name if membership.role else None,
                'status': membership.status,
                'joined_date': membership.joined_date.isoformat() if membership.joined_date else None,
            })
        user_data['memberships'] = memberships
        
        zipf.writestr('user_data.json', json.dumps(user_data, indent=2))
    
    def _backup_user_notifications(self, zipf, user):
        """Backup user's notifications"""
        try:
            notifications = Notification.objects.filter(recipient=user)
            notifications_data = []
            
            for notif in notifications:
                notifications_data.append({
                    'title': notif.title,
                    'message': notif.message,
                    'priority': notif.priority,
                    'in_app_status': notif.in_app_status,
                    'email_status': notif.email_status,
                    'created_at': notif.created_at.isoformat(),
                })
            
            zipf.writestr('notifications.json', json.dumps(notifications_data, indent=2))
        except:
            pass  # Notifications might not exist
    
    def _backup_all_documents(self, zipf):
        """Backup all uploaded documents (for super owner backups)"""
        try:
            documents = DocumentUpload.objects.all()
            documents_data = []
            
            for doc in documents:
                doc_data = {
                    'original_filename': doc.original_filename,
                    'document_type': doc.document_type,
                    'file_size': doc.file_size,
                    'status': doc.status,
                    'created_at': doc.created_at.isoformat(),
                    'activation_request_email': doc.activation_request.email if doc.activation_request else None,
                }
                
                # Add actual file to backup if it exists
                if doc.file and default_storage.exists(doc.file.name):
                    try:
                        with default_storage.open(doc.file.name, 'rb') as f:
                            zipf.writestr(f'documents/{doc.original_filename}', f.read())
                    except Exception as e:
                        logger.warning(f"Could not backup document {doc.original_filename}: {e}")
                
                documents_data.append(doc_data)
            
            zipf.writestr('documents.json', json.dumps(documents_data, indent=2))
        except Exception as e:
            logger.warning(f"Could not backup documents: {e}")
    
    def _create_companies_csv(self, zipf):
        """Create CSV version of companies data"""
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Name', 'Email', 'Description', 'Website', 'Phone', 'Active', 'Created'])
        
        # Data
        for company in Company.objects.all():
            writer.writerow([
                company.name,
                company.email,
                company.description or '',
                company.website or '',
                company.phone or '',
                'Yes' if company.is_active else 'No',
                company.created_at.strftime('%Y-%m-%d')
            ])
        
        zipf.writestr('companies.csv', output.getvalue())
    
    def _create_users_csv(self, zipf):
        """Create CSV version of users data"""
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Username', 'Email', 'First Name', 'Last Name', 'Active', 'Staff', 'Joined'])
        
        # Data
        for user in User.objects.all():
            writer.writerow([
                user.username,
                user.email,
                user.first_name,
                user.last_name,
                'Yes' if user.is_active else 'No',
                'Yes' if user.is_staff else 'No',
                user.date_joined.strftime('%Y-%m-%d')
            ])
        
        zipf.writestr('users.csv', output.getvalue())
    
    def _create_requests_csv(self, zipf):
        """Create CSV version of registration requests data"""
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Date', 'Type', 'Name', 'Email', 'Company', 'Status', 'Approved By'])
        
        # Data
        for req in AccountActivationRequest.objects.select_related('approved_by'):
            writer.writerow([
                req.created_at.strftime('%Y-%m-%d'),
                req.get_request_type_display(),
                f"{req.first_name} {req.last_name}",
                req.email,
                req.company_name or '',
                req.get_status_display(),
                req.approved_by.get_full_name() if req.approved_by else ''
            ])
        
        zipf.writestr('registration_requests.csv', output.getvalue())
    
    @staticmethod
    def list_backups(user):
        """List available backups for a user"""
        backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
        if not os.path.exists(backup_dir):
            return []
        
        backups = []
        for filename in os.listdir(backup_dir):
            if filename.endswith('.zip'):
                file_path = os.path.join(backup_dir, filename)
                stat = os.stat(file_path)
                
                backups.append({
                    'filename': filename,
                    'size': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_mtime),
                    'can_download': BackupManager._can_user_download(user, filename)
                })
        
        return sorted(backups, key=lambda x: x['created_at'], reverse=True)
    
    @staticmethod
    def _can_user_download(user, filename):
        """Check if user can download a specific backup file"""
        # Super owners can download system backups
        if hasattr(user, 'userprofile') and user.userprofile.is_super_owner():
            return True
        
        # Company admins can download their company backups
        if filename.startswith('company_'):
            # Extract company slug from filename
            parts = filename.replace('company_', '').split('_')
            if len(parts) >= 1:
                company_slug = parts[0]
                return Company.objects.filter(
                    slug=company_slug,
                    memberships__user=user,
                    memberships__role__is_admin=True,
                    memberships__status='active'
                ).exists()
        
        # Users can download their own backups
        if filename.startswith(f'user_{user.username}_'):
            return True
        
        return False
    
    @staticmethod
    def cleanup_old_backups(days=30):
        """Clean up backups older than specified days"""
        backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
        if not os.path.exists(backup_dir):
            return
        
        cutoff_time = datetime.now() - timedelta(days=days)
        
        for filename in os.listdir(backup_dir):
            file_path = os.path.join(backup_dir, filename)
            if os.path.isfile(file_path):
                file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                if file_time < cutoff_time:
                    try:
                        os.remove(file_path)
                        logger.info(f"Removed old backup: {filename}")
                    except Exception as e:
                        logger.error(f"Could not remove backup {filename}: {e}")


class RestoreManager:
    """Handle backup restoration"""
    
    def __init__(self, user):
        self.user = user
    
    def restore_from_backup(self, backup_file, restore_type='full'):
        """Restore data from backup file"""
        # This is a complex operation that should be implemented with extreme caution
        # For now, we'll provide the framework
        
        if not self._is_super_owner():
            raise PermissionError("Only super owners can perform system restore")
        
        backup_path = os.path.join(settings.MEDIA_ROOT, 'backups', backup_file)
        if not os.path.exists(backup_path):
            raise FileNotFoundError("Backup file not found")
        
        # Implementation would go here
        # This is a dangerous operation and should include:
        # 1. Database backup before restore
        # 2. Validation of backup file
        # 3. Selective restore options
        # 4. Rollback capability
        
        return {
            'success': True,
            'message': 'Restore functionality available - contact administrator for implementation'
        }
    
    def _is_super_owner(self):
        """Check if user is a super owner"""
        return (
            hasattr(self.user, 'userprofile') and 
            self.user.userprofile.is_super_owner()
        )
