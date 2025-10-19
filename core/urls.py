from django.urls import path
from django.shortcuts import redirect
from . import views
from . import error_test_views
from . import super_owner_views
from . import backup_views

app_name = 'core'

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    
    # Enhanced Registration with Document Upload
    path('register/company/', backup_views.company_registration_request, name='company_registration_request'),
    path('register/individual/', backup_views.individual_registration_request, name='individual_registration_request'),
    path('registration/status/<str:token>/', backup_views.RegistrationWorkflowView.as_view(), name='registration_status'),
    
    # Company Management
    path('company/register/', views.company_register, name='company_register'),  # Legacy endpoint
    path('company/switch/<uuid:company_id>/', views.switch_company, name='switch_company'),
    path('company/manage/', views.company_management, name='company_management'),
    
    # Role Management
    path('roles/create/', views.role_create, name='role_create'),
    path('roles/edit/<int:role_id>/', views.role_edit, name='role_edit'),
    path('roles/delete/<int:role_id>/', views.role_delete, name='role_delete'),
    
    # User Management
    path('users/invite/', views.invite_user, name='invite_user'),
    path('invitation/<str:token>/', views.accept_invitation, name='accept_invitation'),
    
    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notification-preferences/', views.notification_preferences, name='notification_preferences'),
    path('notification-preferences/update/', views.update_notification_preference, name='update_notification_preference'),
    path('admin/notification-settings/', views.admin_notification_settings, name='admin_notification_settings'),
    
    # Supervisor Dashboard
    path('supervisor/', views.supervisor_dashboard, name='supervisor_dashboard'),
    
    # Reports and Analytics
    path('reports/', views.reports_view, name='reports'),
    path('quarterly-summary/', views.quarterly_summary_view, name='quarterly_summary'),
    
    # Company Settings and Management
    path('company/settings/', views.company_settings_view, name='company_settings'),
    path('users/manage/', views.user_management_view, name='user_management'),
    
    # Super Owner Dashboard and Admin Panel
    path('super-owner/', super_owner_views.super_owner_dashboard, name='super_owner_dashboard'),
    path('super-owner/profile/', super_owner_views.super_owner_profile, name='super_owner_profile'),
    path('super-owner/bulk-action/', super_owner_views.bulk_action_requests, name='bulk_action_requests'),
    path('super-owner/export/<str:data_type>/', super_owner_views.export_data, name='export_data'),
    # Legacy admin URLs removed - use Super Owner dashboard instead
    path('admin/documents/<int:document_id>/review/', views.document_review, name='document_review'),
    path('admin/documents/<int:document_id>/download/', views.serve_document, name='serve_document'),
    
    # Enhanced Registration Management
    path('super-owner/registrations/', backup_views.super_owner_registration_management, name='super_owner_registrations'),
    path('super-owner/registrations/process/<uuid:request_id>/', backup_views.process_registration_request, name='process_registration_request'),
    path('super-owner/registrations/bulk-process/', backup_views.bulk_process_requests, name='bulk_process_requests'),
    
    # Backup Management
    path('backup/', backup_views.backup_management, name='backup_management'),
    path('backup/create/', backup_views.create_backup, name='create_backup'),
    path('backup/download/<str:filename>/', backup_views.download_backup, name='download_backup'),
    path('backup/delete/<str:filename>/', backup_views.delete_backup, name='delete_backup'),
    path('backup/api/status/', backup_views.backup_api_status, name='backup_api_status'),
    path('backup/cleanup/', backup_views.cleanup_old_backups, name='cleanup_old_backups'),
    
    # Error Testing (Debug/Staff only)
    path('test-errors/', error_test_views.error_test_panel, name='error_test_panel'),
    path('test-error/', error_test_views.trigger_error, name='trigger_error'),
    path('api/test-error/', error_test_views.error_api_test, name='error_api_test'),
]
