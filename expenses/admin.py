from django.contrib import admin
from .models import Expense, ExpenseCategory, ExpenseAttachment, RecurringExpense

class ExpenseAttachmentInline(admin.TabularInline):
    model = ExpenseAttachment
    extra = 0
    fields = ('name', 'file', 'description')

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'created_by', 'color', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'expense_type', 'status', 'planned_cost', 'actual_cost', 'cost_variance', 'expense_date')
    list_filter = ('status', 'expense_type', 'expense_date', 'created_at', 'is_tax_deductible')
    search_fields = ('name', 'description', 'vendor', 'invoice_number')
    readonly_fields = ('created_at', 'updated_at', 'cost_variance', 'is_over_budget', 'total_cost_with_tax')
    inlines = [ExpenseAttachmentInline]
    date_hierarchy = 'expense_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('created_by', 'project', 'category', 'contractor', 'name', 'description', 'expense_type', 'status')
        }),
        ('Financial Details', {
            'fields': ('planned_cost', 'actual_cost', 'quantity', 'unit', 'unit_cost')
        }),
        ('Dates', {
            'fields': ('expense_date', 'due_date', 'paid_date')
        }),
        ('Documentation', {
            'fields': ('receipt_image', 'invoice_number', 'vendor', 'notes')
        }),
        ('Tax Information', {
            'fields': ('tax_amount', 'is_tax_deductible')
        }),
        ('Calculated Fields', {
            'fields': ('cost_variance', 'is_over_budget', 'total_cost_with_tax'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def cost_variance(self, obj):
        variance = obj.cost_variance
        color = 'red' if variance > 0 else 'green' if variance < 0 else 'black'
        return f'<span style="color: {color}">₦{variance:,.2f}</span>'
    cost_variance.short_description = 'Cost Variance'
    cost_variance.allow_tags = True
    
    def is_over_budget(self, obj):
        return obj.is_over_budget
    is_over_budget.boolean = True
    is_over_budget.short_description = 'Over Budget'
    
    def total_cost_with_tax(self, obj):
        return f"₦{obj.total_cost_with_tax:,.2f}"
    total_cost_with_tax.short_description = 'Total Cost (with Tax)'

@admin.register(ExpenseAttachment)
class ExpenseAttachmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'expense', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'expense__name')

@admin.register(RecurringExpense)
class RecurringExpenseAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'amount', 'frequency', 'next_occurrence', 'is_active')
    list_filter = ('frequency', 'is_active', 'next_occurrence')
    search_fields = ('name', 'project__name')
    date_hierarchy = 'next_occurrence'
