from django.shortcuts import render

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.conf import settings

from .models import SubscriptionPlan, UserSubscription, Payment, BankAccount
from .services import (
    SubscriptionService, StripePaymentService, PaystackPaymentService,
    BankTransferService, InvoiceService
)


@login_required
def subscription_overview(request):
    """Main subscription overview page"""
    subscription_service = SubscriptionService()
    
    # Get user's current subscription
    subscription_info = subscription_service.check_subscription_status(request.user)
    
    # Get available plans for upgrades
    available_plans = subscription_service.get_available_plans()
    plan_comparison = subscription_service.get_plan_comparison()
    
    # Get recent payments
    recent_payments = Payment.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    context = {
        'subscription_info': subscription_info,
        'available_plans': available_plans,
        'plan_comparison': plan_comparison,
        'recent_payments': recent_payments,
        'is_company': hasattr(request.user, 'company_memberships') and request.user.company_memberships.exists(),
    }
    
    return render(request, 'billing/subscription_overview.html', context)


@login_required
def billing_history(request):
    """Billing history and invoices"""
    payments = Payment.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    # Calculate totals
    total_paid = sum(p.amount for p in payments if p.status == 'completed')
    
    context = {
        'payments': payments,
        'total_paid': total_paid,
        'currency': 'USD',  # You can make this dynamic
    }
    
    return render(request, 'billing/billing_history.html', context)


@login_required
def choose_plan(request):
    """Plan selection page"""
    subscription_service = SubscriptionService()
    
    # Get all available plans as a list for the template
    plans = subscription_service.get_available_plans()
    
    # Convert to the format expected by the template
    plan_comparison = []
    for plan in plans:
        plan_data = {
            'id': plan.id,
            'name': plan.name,
            'price': plan.price,
            'billing_period': plan.billing_period,
            'description': plan.description,
            'features': plan.features if isinstance(plan.features, list) else [],
            'is_recommended': plan.name == 'Professional',  # Mark Professional as recommended
            'monthly_equivalent': plan.monthly_equivalent_price,
            'savings': plan.savings_amount,
            'discount_percentage': plan.discount_percentage,
        }
        plan_comparison.append(plan_data)
    
    # Get current subscription
    current_subscription = subscription_service.check_subscription_status(request.user)
    
    context = {
        'plan_comparison': plan_comparison,
        'current_subscription': current_subscription,
        'is_company': hasattr(request.user, 'company_memberships') and request.user.company_memberships.exists(),
    }
    
    return render(request, 'billing/choose_plan.html', context)


@login_required
def payment_method(request, plan_id):
    """Payment method selection"""
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    
    # Get available bank accounts for transfers
    bank_accounts = BankAccount.objects.filter(is_active=True)
    
    context = {
        'plan': plan,
        'bank_accounts': bank_accounts,
        'stripe_public_key': getattr(settings, 'STRIPE_PUBLIC_KEY', ''),
        'paystack_public_key': getattr(settings, 'PAYSTACK_PUBLIC_KEY', ''),
    }
    
    return render(request, 'billing/payment_method.html', context)


@login_required
@require_POST
def cancel_subscription(request):
    """Cancel user's subscription"""
    subscription_service = SubscriptionService()
    result = subscription_service.cancel_subscription(request.user)
    
    if result['success']:
        messages.success(request, 'Your subscription has been cancelled. You can continue using the service until the end of your billing period.')
    else:
        messages.error(request, f"Failed to cancel subscription: {result['error']}")
    
    return redirect('billing:subscription_overview')


# API endpoints for AJAX calls
@login_required
def subscription_status_api(request):
    """API endpoint to get subscription status"""
    subscription_service = SubscriptionService()
    status = subscription_service.check_subscription_status(request.user)
    
    return JsonResponse({
        'success': True,
        'subscription': {
            'has_subscription': status['has_subscription'],
            'is_active': status['is_active'],
            'days_remaining': status['days_remaining'],
            'plan_name': status['plan'].name if status['plan'] else None,
            'billing_period': status['plan'].billing_period if status['plan'] else None,
        }
    })
