from django.core.management.base import BaseCommand
from core.models import Company, NotificationTemplate, Role

class Command(BaseCommand):
    help = 'Create default notification templates for all companies'
    
    def handle(self, *args, **options):
        """Create default notification templates"""
        
        # Default notification configurations
        default_templates = [
            {
                'notification_type': 'expense_created',
                'name': 'New Expense Created',
                'description': 'Notification when a new expense is created',
                'default_priority': 'medium',
                'control_level': 'user_choice',
                'default_in_app': True,
                'default_email': True,
                'default_sms': False,
            },
            {
                'notification_type': 'expense_approved',
                'name': 'Expense Approved',
                'description': 'Notification when an expense is approved',
                'default_priority': 'medium',
                'control_level': 'user_choice',
                'default_in_app': True,
                'default_email': True,
                'default_sms': False,
            },
            {
                'notification_type': 'expense_rejected',
                'name': 'Expense Rejected',
                'description': 'Notification when an expense is rejected',
                'default_priority': 'high',
                'control_level': 'admin_only',
                'default_in_app': True,
                'default_email': True,
                'default_sms': False,
            },
            {
                'notification_type': 'project_overdue',
                'name': 'Project Overdue',
                'description': 'Notification when a project becomes overdue',
                'default_priority': 'urgent',
                'control_level': 'admin_only',
                'default_in_app': True,
                'default_email': True,
                'default_sms': True,
            },
            {
                'notification_type': 'budget_warning',
                'name': 'Budget Warning (75%)',
                'description': 'Notification when budget reaches 75% of limit',
                'default_priority': 'high',
                'control_level': 'admin_default',
                'default_in_app': True,
                'default_email': True,
                'default_sms': False,
            },
            {
                'notification_type': 'budget_critical',
                'name': 'Budget Critical (90%)',
                'description': 'Notification when budget reaches 90% of limit',
                'default_priority': 'urgent',
                'control_level': 'admin_only',
                'default_in_app': True,
                'default_email': True,
                'default_sms': True,
            },
            {
                'notification_type': 'project_milestone',
                'name': 'Project Milestone',
                'description': 'Notification when a project milestone is reached',
                'default_priority': 'medium',
                'control_level': 'user_choice',
                'default_in_app': True,
                'default_email': False,
                'default_sms': False,
            },
            {
                'notification_type': 'user_invited',
                'name': 'User Invited',
                'description': 'Notification when a new user is invited',
                'default_priority': 'medium',
                'control_level': 'role_based',
                'default_in_app': True,
                'default_email': True,
                'default_sms': False,
            },
            {
                'notification_type': 'role_changed',
                'name': 'Role Changed',
                'description': 'Notification when user role is changed',
                'default_priority': 'high',
                'control_level': 'admin_only',
                'default_in_app': True,
                'default_email': True,
                'default_sms': False,
            },
            {
                'notification_type': 'security_alert',
                'name': 'Security Alert',
                'description': 'Important security notifications',
                'default_priority': 'urgent',
                'control_level': 'admin_only',
                'default_in_app': True,
                'default_email': True,
                'default_sms': True,
            },
            {
                'notification_type': 'system_maintenance',
                'name': 'System Maintenance',
                'description': 'Notifications about system maintenance',
                'default_priority': 'medium',
                'control_level': 'admin_only',
                'default_in_app': True,
                'default_email': True,
                'default_sms': False,
            },
            {
                'notification_type': 'report_ready',
                'name': 'Report Ready',
                'description': 'Notification when a report is ready for download',
                'default_priority': 'low',
                'control_level': 'user_choice',
                'default_in_app': True,
                'default_email': False,
                'default_sms': False,
            },
        ]
        
        companies = Company.objects.all()
        created_count = 0
        
        for company in companies:
            self.stdout.write(f"Processing company: {company.name}")
            
            for template_data in default_templates:
                template, created = NotificationTemplate.objects.get_or_create(
                    company=company,
                    notification_type=template_data['notification_type'],
                    defaults=template_data
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"  Created: {template.name}")
                    )
                
                # Set role-based permissions for specific notifications
                if template_data['control_level'] == 'role_based':
                    if template_data['notification_type'] == 'user_invited':
                        # Only admins and supervisors can receive user invitation notifications
                        admin_roles = list(Role.objects.filter(
                            company=company,
                            is_admin=True
                        ))
                        supervisor_roles = list(Role.objects.filter(
                            company=company,
                            is_supervisor=True
                        ))
                        all_roles = admin_roles + supervisor_roles
                        template.allowed_roles.set(all_roles)
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} notification templates')
        )
