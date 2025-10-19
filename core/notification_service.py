from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from .models import Notification, Company
from typing import List, Optional

class NotificationService:
    """
    Service class for creating and managing notifications
    """
    
    @staticmethod
    def create_notification(
        company: Company,
        recipient: User,
        notification_type: str,
        title: str,
        message: str,
        priority: str = 'medium',
        sender: Optional[User] = None,
        related_object=None,
        send_email: bool = True
    ) -> Notification:
        """
        Create a new notification
        """
        # Get or create a default notification template for this type
        from .models import NotificationTemplate
        try:
            template = NotificationTemplate.objects.get(
                company=company,
                notification_type=notification_type
            )
        except NotificationTemplate.DoesNotExist:
            # Create a basic template if it doesn't exist
            template = NotificationTemplate.objects.create(
                company=company,
                notification_type=notification_type,
                name=notification_type.replace('_', ' ').title(),
                description=f'Notification for {notification_type}',
                default_priority=priority
            )
        
        notification = Notification.objects.create(
            company=company,
            recipient=recipient,
            sender=sender,
            notification_template=template,
            title=title,
            message=message,
            priority=priority
        )
        
        # Set related object if provided
        if related_object:
            notification.content_type = related_object._meta.model
            notification.object_id = related_object.pk
            notification.save()
        
        # Send email notification if requested and user preferences allow
        if send_email:
            NotificationService.send_email_notification(notification)
        
        return notification
    
    @staticmethod
    def send_email_notification(notification: Notification) -> bool:
        """
        Send email notification to recipient
        """
        try:
            # Check user's notification preferences
            profile = getattr(notification.recipient, 'userprofile', None)
            if profile and profile.notification_preferences:
                email_enabled = profile.notification_preferences.get('email_notifications', True)
                if not email_enabled:
                    return False
            
            subject = f"[{notification.company.name}] {notification.title}"
            
            # Use template for email content
            context = {
                'notification': notification,
                'company': notification.company,
                'recipient': notification.recipient,
            }
            
            html_message = render_to_string('core/emails/notification.html', context)
            plain_message = render_to_string('core/emails/notification.txt', context)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[notification.recipient.email],
                html_message=html_message,
                fail_silently=True,
            )
            
            notification.email_status = 'sent'
            notification.email_sent_at = timezone.now()
            notification.save(update_fields=['email_status', 'email_sent_at'])
            return True
            
        except Exception as e:
            print(f"Failed to send email notification: {e}")
            return False
    
    @staticmethod
    def notify_expense_created(expense, created_by: User):
        """
        Notify relevant users when an expense is created
        """
        company = expense.project.company
        
        # Notify project assigned users and supervisors
        recipients = []
        
        # Add project assigned users
        for user in expense.project.assigned_to.all():
            if user != created_by:
                recipients.append(user)
        
        # Add supervisors
        supervisors = company.memberships.filter(
            role__is_supervisor=True,
            status='active'
        ).exclude(user=created_by)
        
        for membership in supervisors:
            recipients.append(membership.user)
        
        # Remove duplicates
        recipients = list(set(recipients))
        
        for recipient in recipients:
            NotificationService.create_notification(
                company=company,
                recipient=recipient,
                notification_type='expense_created',
                title=f'New Expense Created: {expense.name}',
                message=f'{created_by.get_full_name()} created a new expense \"{expense.name}\" for project \"{expense.project.name}\" worth ₦{expense.actual_cost}.',
                priority='medium',
                sender=created_by,
                related_object=expense
            )
    
    @staticmethod
    def notify_expense_approved(expense, approved_by: User):
        """
        Notify when expense is approved
        """
        company = expense.project.company
        
        # Notify the person who created the expense
        if expense.created_by != approved_by:
            NotificationService.create_notification(
                company=company,
                recipient=expense.created_by,
                notification_type='expense_approved',
                title=f'Expense Approved: {expense.name}',
                message=f'Your expense \"{expense.name}\" for project \"{expense.project.name}\" has been approved by {approved_by.get_full_name()}.',
                priority='medium',
                sender=approved_by,
                related_object=expense
            )
    
    @staticmethod
    def notify_project_milestone(project, milestone_message: str, created_by: User):
        """
        Notify about project milestones
        """
        company = project.company
        
        # Notify assigned users and supervisors
        recipients = list(project.assigned_to.all())
        
        # Add supervisors
        supervisors = company.memberships.filter(
            role__is_supervisor=True,
            status='active'
        )
        
        for membership in supervisors:
            recipients.append(membership.user)
        
        # Remove duplicates and sender
        recipients = list(set(recipients))
        if created_by in recipients:
            recipients.remove(created_by)
        
        for recipient in recipients:
            NotificationService.create_notification(
                company=company,
                recipient=recipient,
                notification_type='project_milestone',
                title=f'Project Milestone: {project.name}',
                message=milestone_message,
                priority='medium',
                sender=created_by,
                related_object=project
            )
    
    @staticmethod
    def notify_budget_warning(project, warning_message: str):
        """
        Notify about budget warnings
        """
        company = project.company
        
        # Notify supervisors and admins
        recipients = []
        
        memberships = company.memberships.filter(
            status='active'
        )
        
        from django.db import models
        memberships = memberships.filter(
            models.Q(role__is_supervisor=True) | models.Q(role__is_admin=True)
        )
        
        for membership in memberships:
            recipients.append(membership.user)
        
        for recipient in recipients:
            NotificationService.create_notification(
                company=company,
                recipient=recipient,
                notification_type='budget_warning',
                title=f'Budget Warning: {project.name}',
                message=warning_message,
                priority='high',
                related_object=project
            )
    
    @staticmethod
    def notify_user_invited(company: Company, invited_user: User, invited_by: User, role):
        """
        Notify when user is invited to company
        """
        NotificationService.create_notification(
            company=company,
            recipient=invited_user,
            notification_type='user_invited',
            title=f'Welcome to {company.name}',
            message=f'You have been invited to join {company.name} with the role of {role.name} by {invited_by.get_full_name()}.',
            priority='medium',
            sender=invited_by
        )
    
    @staticmethod
    def notify_role_changed(membership, old_role, new_role, changed_by: User):
        """
        Notify when user's role is changed
        """
        old_role_name = old_role.name if old_role else "No Role"
        message = f'Your role in {membership.company.name} has been changed from {old_role_name} to {new_role.name} by {changed_by.get_full_name()}.'
        
        NotificationService.create_notification(
            company=membership.company,
            recipient=membership.user,
            notification_type='role_changed',
            title='Your Role Has Been Updated',
            message=message,
            priority='medium',
            sender=changed_by
        )
    
    @staticmethod
    def get_unread_count(user: User, company: Company = None) -> int:
        """
        Get count of unread notifications for user
        """
        queryset = Notification.objects.filter(recipient=user, read_at__isnull=True)
        if company:
            queryset = queryset.filter(company=company)
        return queryset.count()
    
    @staticmethod
    def mark_all_read(user: User, company: Company = None):
        """
        Mark all notifications as read for user
        """
        queryset = Notification.objects.filter(recipient=user, read_at__isnull=True)
        if company:
            queryset = queryset.filter(company=company)
        
        queryset.update(
            read_at=timezone.now(),
            in_app_status='read'
        )
