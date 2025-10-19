from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import uuid


class SubscriptionPlan(models.Model):
    BILLING_PERIODS = [
        ('monthly', 'Monthly'),
        ('annual', 'Annual'),
        ('decade', 'Decade (10 Years)'),
    ]
    
    name = models.CharField(max_length=100)
    billing_period = models.CharField(max_length=20, choices=BILLING_PERIODS)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    features = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Discount percentages
    discount_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        help_text="Discount percentage compared to monthly equivalent"
    )
    
    class Meta:
        unique_together = ['name', 'billing_period']
        ordering = ['billing_period', 'price']
    
    def __str__(self):
        return f"{self.name} - {self.get_billing_period_display()}"
    
    @property
    def monthly_equivalent_price(self):
        """Calculate monthly equivalent price for comparison"""
        if self.billing_period == 'monthly':
            return self.price
        elif self.billing_period == 'annual':
            return self.price / 12
        elif self.billing_period == 'decade':
            return self.price / 120  # 10 years * 12 months
        return self.price
    
    @property
    def savings_amount(self):
        """Calculate savings amount compared to monthly billing"""
        if self.billing_period == 'monthly':
            return Decimal('0.00')
        
        monthly_plan = SubscriptionPlan.objects.filter(
            name=self.name, 
            billing_period='monthly',
            is_active=True
        ).first()
        
        if not monthly_plan:
            return Decimal('0.00')
        
        if self.billing_period == 'annual':
            monthly_total = monthly_plan.price * 12
            return monthly_total - self.price
        elif self.billing_period == 'decade':
            monthly_total = monthly_plan.price * 120
            return monthly_total - self.price
        
        return Decimal('0.00')


class UserSubscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('pending', 'Pending'),
        ('suspended', 'Suspended'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    auto_renew = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Stripe/Paystack subscription IDs
    stripe_subscription_id = models.CharField(max_length=200, blank=True, null=True)
    paystack_subscription_id = models.CharField(max_length=200, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.plan}"
    
    @property
    def is_active(self):
        return self.status == 'active' and self.end_date > timezone.now()
    
    @property
    def days_remaining(self):
        if self.end_date > timezone.now():
            return (self.end_date - timezone.now()).days
        return 0
    
    def calculate_end_date(self):
        """Calculate end date based on plan billing period"""
        start = self.start_date or timezone.now()
        
        if self.plan.billing_period == 'monthly':
            from dateutil.relativedelta import relativedelta
            return start + relativedelta(months=1)
        elif self.plan.billing_period == 'annual':
            from dateutil.relativedelta import relativedelta
            return start + relativedelta(years=1)
        elif self.plan.billing_period == 'decade':
            from dateutil.relativedelta import relativedelta
            return start + relativedelta(years=10)
        
        return start
    
    def save(self, *args, **kwargs):
        if not self.end_date:
            self.end_date = self.calculate_end_date()
        super().save(*args, **kwargs)


class Payment(models.Model):
    PAYMENT_METHODS = [
        ('stripe', 'Stripe (Card)'),
        ('paystack', 'Paystack (Card)'),
        ('bank_transfer', 'Bank Transfer'),
        ('wire_transfer', 'Wire Transfer'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Transaction IDs from payment processors
    stripe_payment_intent_id = models.CharField(max_length=200, blank=True, null=True)
    paystack_reference = models.CharField(max_length=200, blank=True, null=True)
    bank_reference = models.CharField(max_length=200, blank=True, null=True)
    
    # Payment metadata
    metadata = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment {self.id} - {self.user.username} - {self.amount} {self.currency}"


class BankAccount(models.Model):
    """Company bank accounts for receiving payments"""
    ACCOUNT_TYPES = [
        ('local', 'Local Account'),
        ('international', 'International Account'),
    ]
    
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50)
    routing_number = models.CharField(max_length=50, blank=True)
    swift_code = models.CharField(max_length=20, blank=True)
    iban = models.CharField(max_length=50, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} - {self.bank_name} ({self.currency})"


class Invoice(models.Model):
    """Invoice generation for payments"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='invoice')
    invoice_number = models.CharField(max_length=50, unique=True)
    issue_date = models.DateTimeField(default=timezone.now)
    due_date = models.DateTimeField()
    
    # Invoice details
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Invoice {self.invoice_number}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            from datetime import datetime
            self.invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{str(self.id)[:8].upper()}"
        
        # Calculate tax amount
        self.tax_amount = (self.subtotal * self.tax_rate) / 100
        self.total_amount = self.subtotal + self.tax_amount
        
        super().save(*args, **kwargs)


class PaymentNotification(models.Model):
    """Track payment notifications and webhooks"""
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50)
    provider = models.CharField(max_length=20)  # stripe, paystack, etc.
    webhook_data = models.JSONField()
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.provider} - {self.notification_type} - {self.payment.id}"
