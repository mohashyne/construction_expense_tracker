from django.contrib import admin
from .models import Contractor

@admin.register(Contractor)
class ContractorAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'company_name', 'contractor_type', 'email', 'phone', 'hourly_rate', 'rating', 'is_active', 'created_at')
    list_filter = ('contractor_type', 'is_active', 'created_at', 'rating')
    search_fields = ('name', 'company_name', 'email', 'phone', 'license_number')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('company', 'created_by', 'name', 'company_name', 'contractor_type')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'address')
        }),
        ('Professional Details', {
            'fields': ('license_number', 'hourly_rate', 'rating', 'is_active')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
