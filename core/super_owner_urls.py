from django.urls import path
from . import super_owner_views
from . import debug_views

app_name = 'super_owner'

urlpatterns = [
    # Main Super Owner Dashboard
    path('', super_owner_views.super_owner_dashboard, name='dashboard'),
    
    # Companies Management (Full CRUD)
    path('companies/', super_owner_views.companies_list, name='companies_list'),
    path('companies/<uuid:company_id>/', super_owner_views.company_detail, name='company_detail'),
    path('companies/<uuid:company_id>/toggle-status/', super_owner_views.company_toggle_status, name='company_toggle_status'),
    
    # Users Management (Full CRUD)
    path('users/', super_owner_views.users_list, name='users_list'),
    path('users/<int:user_id>/', super_owner_views.user_detail, name='user_detail'),
    path('users/<int:user_id>/toggle-status/', super_owner_views.user_toggle_status, name='user_toggle_status'),
    
    # Registration Requests Management
    path('registration-requests/', super_owner_views.activation_requests_list, name='activation_requests_list'),
    path('registration-requests/<uuid:request_id>/approve/', super_owner_views.approve_activation_request, name='approve_activation_request'),
    path('registration-requests/<uuid:request_id>/reject/', super_owner_views.reject_activation_request, name='reject_activation_request'),
    path('registration-requests/bulk-action/', super_owner_views.bulk_action_requests, name='bulk_action_requests'),
    
    # System Management
    path('system/', super_owner_views.system_management, name='system_management'),
    path('analytics/', super_owner_views.system_analytics, name='system_analytics'),
    path('backup/', super_owner_views.super_owner_backup_management, name='backup_management'),
    path('notifications/', super_owner_views.super_owner_notifications, name='notifications'),
    
    # Export Functions
    path('export/<str:data_type>/', super_owner_views.export_data, name='export_data'),
    
    # Super Owner Management (Delegation)
    path('super-owners/', super_owner_views.manage_super_owners, name='manage_super_owners'),
    path('super-owners/create/', super_owner_views.create_super_owner, name='create_super_owner'),
    
    # API Endpoints
    path('api/company/<uuid:company_id>/stats/', super_owner_views.company_stats_api, name='company_stats_api'),
    
    # Legacy support
    path('dashboard/', super_owner_views.super_owner_dashboard, name='dashboard_legacy'),
    
    # Debug endpoints (only for troubleshooting)
    path('debug/permissions/', debug_views.user_permissions_debug, name='debug_permissions'),
    path('debug/all-users/', debug_views.all_users_permissions_debug, name='debug_all_users'),
]
