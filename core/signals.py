from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from decimal import Decimal

from .models import CompanyMembership, UserProfile
from .notification_service import NotificationService

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create user profile when user is created
    """
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Save user profile when user is saved
    """
    if hasattr(instance, 'userprofile'):
        instance.userprofile.save()

@receiver(post_save, sender='expenses.Expense')
def expense_created_notification(sender, instance, created, **kwargs):
    """
    Send notification when expense is created
    """
    if created and instance.created_by:
        NotificationService.notify_expense_created(instance, instance.created_by)

@receiver(pre_save, sender='expenses.Expense')
def expense_status_changed(sender, instance, **kwargs):
    """
    Track expense status changes for notifications
    """
    if instance.pk:
        try:
            old_expense = sender.objects.get(pk=instance.pk)
            # Store previous status for comparison
            instance._previous_status = old_expense.status
        except sender.DoesNotExist:
            instance._previous_status = None

@receiver(post_save, sender='expenses.Expense')
def expense_approved_notification(sender, instance, created, **kwargs):
    """
    Send notification when expense is approved
    """
    if not created and hasattr(instance, '_previous_status'):
        if (instance._previous_status == 'planned' and 
            instance.status == 'approved' and 
            instance.approved_by):
            NotificationService.notify_expense_approved(instance, instance.approved_by)

@receiver(post_save, sender='projects.Project')
def project_budget_warning(sender, instance, created, **kwargs):
    """
    Check for budget warnings when project is updated
    """
    if not created:
        # Check if project is over budget
        if instance.is_over_budget:
            budget_percentage = (instance.total_expenses / instance.total_budget) * 100
            if budget_percentage > 90:  # Warn when over 90% of budget is used
                warning_message = f"Project '{instance.name}' has exceeded {budget_percentage:.1f}% of its budget. Current spending: ₦{instance.total_expenses}, Budget: ₦{instance.total_budget}"
                NotificationService.notify_budget_warning(instance, warning_message)

@receiver(post_save, sender='projects.Project')
def project_milestone_notification(sender, instance, created, **kwargs):
    """
    Notify about project milestones
    """
    if not created and hasattr(instance, '_milestone_message'):
        # This would be set by the view when a milestone is reached
        NotificationService.notify_project_milestone(
            instance, 
            instance._milestone_message, 
            instance._milestone_user
        )

@receiver(post_save, sender=CompanyMembership)
def user_invited_notification(sender, instance, created, **kwargs):
    """
    Send notification when user is invited to company
    """
    if created and instance.status == 'invited' and instance.invited_by:
        # For invited users who don't have an account yet
        if not instance.user:
            # We can't send notification to non-existent user
            # Email invitation is handled in views
            pass
        else:
            # For existing users who are added to company
            NotificationService.notify_user_invited(
                instance.company, 
                instance.user, 
                instance.invited_by, 
                instance.role
            )

@receiver(pre_save, sender=CompanyMembership)
def track_role_changes(sender, instance, **kwargs):
    """
    Track role changes for notifications
    """
    if instance.pk:
        try:
            old_membership = sender.objects.get(pk=instance.pk)
            instance._previous_role = old_membership.role
        except sender.DoesNotExist:
            instance._previous_role = None

@receiver(post_save, sender=CompanyMembership)
def role_changed_notification(sender, instance, created, **kwargs):
    """
    Notify when user's role is changed
    """
    if (not created and 
        hasattr(instance, '_previous_role') and 
        instance._previous_role != instance.role and
        hasattr(instance, '_changed_by')):
        
        NotificationService.notify_role_changed(
            instance,
            instance._previous_role,
            instance.role,
            instance._changed_by
        )

# Context processors for templates
def notification_context(request):
    """
    Add notification data to template context
    """
    if request.user.is_authenticated:
        current_company = getattr(request, 'current_company', None)
        unread_count = NotificationService.get_unread_count(request.user, current_company)
        
        # Get recent notifications
        recent_notifications = request.user.notifications.filter(
            company=current_company if current_company else None
        ).order_by('-created_at')[:5]
        
        return {
            'unread_notification_count': unread_count,
            'recent_notifications': recent_notifications,
        }
    
    return {
        'unread_notification_count': 0,
        'recent_notifications': [],
    }

# Utility functions for views
def add_milestone_notification(project, message, user):
    """
    Helper function to add milestone notification data to project
    """
    project._milestone_message = message
    project._milestone_user = user

def add_role_change_tracking(membership, changed_by_user):
    """
    Helper function to track who changed a role
    """
    membership._changed_by = changed_by_user
