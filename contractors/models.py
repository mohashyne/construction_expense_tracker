from django.db import models
from django.contrib.auth.models import User
from core.models import TimeStampedModel

class Contractor(TimeStampedModel):
    CONTRACTOR_TYPES = [
        ('general', 'General Contractor'),
        ('electrical', 'Electrical'),
        ('plumbing', 'Plumbing'),
        ('hvac', 'HVAC'),
        ('roofing', 'Roofing'),
        ('flooring', 'Flooring'),
        ('painting', 'Painting'),
        ('landscaping', 'Landscaping'),
        ('other', 'Other'),
    ]
    
    company = models.ForeignKey('core.Company', on_delete=models.CASCADE, related_name='contractors', null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200, blank=True)
    contractor_type = models.CharField(max_length=20, choices=CONTRACTOR_TYPES, default='general')
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    license_number = models.CharField(max_length=100, blank=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['name']
        unique_together = ['company', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.company_name or self.get_contractor_type_display()}"
