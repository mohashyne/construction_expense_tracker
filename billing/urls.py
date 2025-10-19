from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    # Main billing pages
    path('', views.subscription_overview, name='subscription_overview'),
    path('subscription/', views.subscription_overview, name='subscription_overview'),
    path('history/', views.billing_history, name='billing_history'),
    path('choose-plan/', views.choose_plan, name='choose_plan'),
    path('payment-method/<int:plan_id>/', views.payment_method, name='payment_method'),
    
    # Actions
    path('cancel/', views.cancel_subscription, name='cancel_subscription'),
    
    # API endpoints
    path('api/subscription-status/', views.subscription_status_api, name='subscription_status_api'),
]
