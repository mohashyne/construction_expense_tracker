from django.contrib import admin
from django.utils.html import format_html
from .models import (
    SubscriptionPlan, UserSubscription, Payment, 
    BankAccount, Invoice, PaymentNotification
)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'billing_period', 'price', 'discount_percentage', 
        'is_active', 'created_at'
    ]
    list_filter = ['billing_period', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['billing_period', 'price']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'billing_period', 'price', 'description')
        }),
        ('Features & Benefits', {
            'fields': ('features', 'discount_percentage')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'plan', 'status', 'start_date', 'end_date', 
        'days_remaining_display', 'auto_renew'
    ]
    list_filter = ['status', 'plan__billing_period', 'auto_renew', 'start_date']
    search_fields = ['user__username', 'user__email', 'plan__name']
    date_hierarchy = 'start_date'
    readonly_fields = ['created_at', 'updated_at', 'days_remaining_display']
    
    def days_remaining_display(self, obj):
        days = obj.days_remaining
        if days > 0:
            color = 'green' if days > 30 else 'orange' if days > 7 else 'red'
            return format_html(
                '<span style="color: {}">{} days</span>',
                color, days
            )
        return format_html('<span style="color: red">Expired</span>')
    days_remaining_display.short_description = 'Days Remaining'
    
    fieldsets = (
        ('Subscription Details', {
            'fields': ('user', 'plan', 'status')
        }),
        ('Duration', {
            'fields': ('start_date', 'end_date', 'auto_renew')
        }),
        ('Payment Integration', {
            'fields': ('stripe_subscription_id', 'paystack_subscription_id'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'amount_display', 'payment_method', 
        'status', 'created_at', 'completed_at'
    ]
    list_filter = ['status', 'payment_method', 'currency', 'created_at']
    search_fields = [
        'user__username', 'user__email', 'stripe_payment_intent_id', 
        'paystack_reference', 'bank_reference'
    ]
    date_hierarchy = 'created_at'
    readonly_fields = ['id', 'created_at', 'completed_at']
    
    def amount_display(self, obj):
        return f"{obj.amount} {obj.currency}"
    amount_display.short_description = 'Amount'
    
    fieldsets = (
        ('Payment Details', {
            'fields': ('user', 'subscription', 'amount', 'currency', 'payment_method')
        }),
        ('Status', {
            'fields': ('status', 'completed_at')
        }),
        ('Transaction IDs', {
            'fields': (
                'stripe_payment_intent_id', 'paystack_reference', 'bank_reference'
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'bank_name', 'account_type', 'currency', 'is_active'
    ]
    list_filter = ['account_type', 'currency', 'is_active']
    search_fields = ['name', 'bank_name', 'account_number']
    
    fieldsets = (
        ('Account Information', {
            'fields': ('name', 'bank_name', 'account_number', 'account_type', 'currency')
        }),
        ('Routing Information', {
            'fields': ('routing_number', 'swift_code', 'iban')
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'payment', 'total_amount_display', 
        'issue_date', 'due_date'
    ]
    list_filter = ['issue_date', 'due_date']
    search_fields = ['invoice_number', 'payment__user__username']
    date_hierarchy = 'issue_date'
    readonly_fields = ['id', 'tax_amount', 'total_amount']
    
    def total_amount_display(self, obj):
        return f"{obj.total_amount} {obj.payment.currency}"
    total_amount_display.short_description = 'Total Amount'
    
    fieldsets = (
        ('Invoice Details', {
            'fields': ('payment', 'invoice_number', 'issue_date', 'due_date')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'tax_rate', 'tax_amount', 'total_amount')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        })
    )


@admin.register(PaymentNotification)
class PaymentNotificationAdmin(admin.ModelAdmin):
    list_display = [
        'payment', 'provider', 'notification_type', 'processed', 'created_at'
    ]
    list_filter = ['provider', 'notification_type', 'processed', 'created_at']
    search_fields = ['payment__id', 'notification_type']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Notification Details', {
            'fields': ('payment', 'provider', 'notification_type', 'processed')
        }),
        ('Webhook Data', {
            'fields': ('webhook_data',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
