from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from core.models import TimeStampedModel
from projects.models import Project
from contractors.models import Contractor

class ExpenseCategory(TimeStampedModel):
    """Categories for organizing expenses"""
    company = models.ForeignKey('core.Company', on_delete=models.CASCADE, related_name='expense_categories', null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff', help_text='Hex color code for charts')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = 'Expense Categories'
        unique_together = ['company', 'name']
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Expense(TimeStampedModel):
    """Individual expense records"""
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    EXPENSE_TYPES = [
        ('material', 'Material'),
        ('labor', 'Labor'),
        ('equipment', 'Equipment'),
        ('permit', 'Permit'),
        ('utility', 'Utility'),
        ('transportation', 'Transportation'),
        ('insurance', 'Insurance'),
        ('other', 'Other'),
    ]
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='expenses')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_expenses')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, blank=True)
    contractor = models.ForeignKey(Contractor, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Basic details
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    expense_type = models.CharField(max_length=20, choices=EXPENSE_TYPES, default='other')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    
    # Financial details
    planned_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    actual_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    
    # Dates
    expense_date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    paid_date = models.DateField(null=True, blank=True)
    
    # Additional details
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)
    unit = models.CharField(max_length=50, blank=True, help_text='Unit of measurement')
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Documentation
    receipt_image = models.ImageField(upload_to='receipts/', blank=True, null=True)
    invoice_number = models.CharField(max_length=100, blank=True)
    vendor = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    
    # Tax information
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    is_tax_deductible = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-expense_date', '-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.project.name} (₦{self.actual_cost})"
    
    @property
    def cost_variance(self):
        """Calculate variance between planned and actual cost"""
        return self.actual_cost - self.planned_cost
    
    @property
    def is_over_budget(self):
        """Check if expense is over planned budget"""
        return self.actual_cost > self.planned_cost
    
    @property
    def total_cost_with_tax(self):
        """Calculate total cost including tax"""
        return self.actual_cost + self.tax_amount
    
    def save(self, *args, **kwargs):
        # Auto-calculate actual cost if unit cost and quantity are provided
        if self.unit_cost and self.quantity:
            self.actual_cost = self.unit_cost * self.quantity
        super().save(*args, **kwargs)

class ExpenseAttachment(TimeStampedModel):
    """Additional file attachments for expenses"""
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='expense_attachments/')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.expense.name} - {self.name}"

class RecurringExpense(TimeStampedModel):
    """Template for recurring expenses"""
    FREQUENCY_CHOICES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annually', 'Annually'),
    ]
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='recurring_expenses')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, blank=True)
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    next_occurrence = models.DateField()
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['next_occurrence']
    
    def __str__(self):
        return f"{self.name} - {self.get_frequency_display()} (₦{self.amount})"
