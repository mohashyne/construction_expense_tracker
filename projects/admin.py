from django.contrib import admin
from .models import Project, ProjectContractor

class ProjectContractorInline(admin.TabularInline):
    model = ProjectContractor
    extra = 0
    fields = ('contractor', 'role', 'start_date', 'end_date', 'hourly_rate', 'is_active')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'created_by', 'status', 'priority', 'total_budget', 'progress_percentage', 'created_at')
    list_filter = ('status', 'priority', 'created_at', 'expected_completion_date')
    search_fields = ('name', 'description', 'location', 'client_name')
    readonly_fields = ('created_at', 'updated_at', 'total_expenses', 'budget_variance')
    inlines = [ProjectContractorInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('company', 'created_by', 'name', 'description', 'location', 'status', 'priority')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date', 'expected_completion_date')
        }),
        ('Budget', {
            'fields': ('total_budget',)
        }),
        ('Client Information', {
            'fields': ('client_name', 'client_email', 'client_phone')
        }),
        ('Progress', {
            'fields': ('progress_percentage', 'image')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def total_expenses(self, obj):
        return f"₦{obj.total_expenses:,.2f}"
    total_expenses.short_description = 'Total Expenses'
    
    def budget_variance(self, obj):
        variance = obj.budget_variance
        color = 'green' if variance >= 0 else 'red'
        return f'<span style="color: {color}">₦{variance:,.2f}</span>'
    budget_variance.short_description = 'Budget Variance'
    budget_variance.allow_tags = True

@admin.register(ProjectContractor)
class ProjectContractorAdmin(admin.ModelAdmin):
    list_display = ('project', 'contractor', 'role', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active', 'start_date', 'end_date')
    search_fields = ('project__name', 'contractor__name', 'role')
