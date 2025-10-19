from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from core.models import TimeStampedModel

class Project(TimeStampedModel):
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    company = models.ForeignKey('core.Company', on_delete=models.CASCADE, related_name='projects', null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    assigned_to = models.ManyToManyField(User, blank=True, related_name='assigned_projects')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Dates
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    expected_completion_date = models.DateField(null=True, blank=True)
    
    # Budget
    total_budget = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    
    # Project details
    client_name = models.CharField(max_length=200, blank=True)
    client_email = models.EmailField(blank=True)
    client_phone = models.CharField(max_length=20, blank=True)
    
    # Progress tracking
    progress_percentage = models.IntegerField(default=0, help_text="Progress percentage (0-100)")
    
    # File attachments
    image = models.ImageField(upload_to='projects/', blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['company', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"
    
    @property
    def total_expenses(self):
        """Calculate total actual expenses for this project"""
        return self.expenses.aggregate(
            total=models.Sum('actual_cost')
        )['total'] or Decimal('0.00')
    
    @property
    def total_planned_expenses(self):
        """Calculate total planned expenses for this project"""
        return self.expenses.aggregate(
            total=models.Sum('planned_cost')
        )['total'] or Decimal('0.00')
    
    @property
    def budget_variance(self):
        """Calculate budget variance (negative means over budget)"""
        return self.total_budget - self.total_expenses
    
    @property
    def is_over_budget(self):
        """Check if project is over budget"""
        return self.total_expenses > self.total_budget
    
    @property
    def days_remaining(self):
        """Calculate days remaining until expected completion"""
        if self.expected_completion_date:
            today = timezone.now().date()
            return (self.expected_completion_date - today).days
        return None
    
    @property
    def is_overdue(self):
        """Check if project is overdue"""
        if self.expected_completion_date and self.status != 'completed':
            return timezone.now().date() > self.expected_completion_date
        return False

class ProjectContractor(TimeStampedModel):
    """Many-to-many relationship between projects and contractors with additional fields"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_contractors')
    contractor = models.ForeignKey('contractors.Contractor', on_delete=models.CASCADE, related_name='contractor_projects')
    role = models.CharField(max_length=100, help_text="Role in this project")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['project', 'contractor', 'role']
    
    def __str__(self):
        return f"{self.project.name} - {self.contractor.name} ({self.role})"
