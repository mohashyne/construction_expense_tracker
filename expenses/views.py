from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Expense, ExpenseCategory
from core.views import get_current_company
import logging

logger = logging.getLogger(__name__)

@login_required
def expense_list(request):
    """List all expenses for the current user"""
    current_company = get_current_company(request)
    if not current_company:
        messages.warning(request, 'Please select a company to view expenses.')
        return redirect('core:company_register')
    expenses = Expense.objects.filter(project__company=current_company)
    return render(request, 'expenses/list.html', {'expenses': expenses})

@login_required
def expense_detail(request, pk):
    """Expense detail view"""
    current_company = get_current_company(request)
    expense = get_object_or_404(Expense, pk=pk, project__company=current_company)
    return render(request, 'expenses/detail.html', {'expense': expense})

@login_required
def expense_create(request):
    """Create new expense"""
    if request.method == 'POST':
        # Add form handling here
        messages.success(request, 'Expense created successfully!')
        return redirect('expenses:list')
    return render(request, 'expenses/create.html')

@login_required
def expense_edit(request, pk):
    """Edit existing expense"""
    current_company = get_current_company(request)
    expense = get_object_or_404(Expense, pk=pk, project__company=current_company)
    if request.method == 'POST':
        # Add form handling here
        messages.success(request, 'Expense updated successfully!')
        return redirect('expenses:detail', pk=pk)
    return render(request, 'expenses/edit.html', {'expense': expense})

@login_required
def expense_delete(request, pk):
    """Delete expense"""
    current_company = get_current_company(request)
    expense = get_object_or_404(Expense, pk=pk, project__company=current_company)
    if request.method == 'POST':
        expense.delete()
        messages.success(request, 'Expense deleted successfully!')
        return redirect('expenses:list')
    return render(request, 'expenses/delete.html', {'expense': expense})

@login_required
def category_list(request):
    """List expense categories"""
    current_company = get_current_company(request)
    if not current_company:
        return redirect('core:company_register')
    categories = ExpenseCategory.objects.filter(company=current_company, is_active=True)
    return render(request, 'expenses/categories.html', {'categories': categories})
