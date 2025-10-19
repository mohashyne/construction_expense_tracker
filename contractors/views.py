from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Contractor
from .forms import ContractorForm
from core.views import get_current_company
import logging

logger = logging.getLogger(__name__)

@login_required
def contractor_list(request):
    """List all contractors for the current user"""
    current_company = get_current_company(request)
    if not current_company:
        messages.warning(request, 'Please select a company to view contractors.')
        return redirect('core:company_register')
    contractors = Contractor.objects.filter(company=current_company, is_active=True)
    return render(request, 'contractors/list.html', {'contractors': contractors})

@login_required
def contractor_detail(request, pk):
    """Contractor detail view"""
    current_company = get_current_company(request)
    contractor = get_object_or_404(Contractor, pk=pk, company=current_company)
    return render(request, 'contractors/detail.html', {'contractor': contractor})

@login_required
def contractor_create(request):
    """Create new contractor"""
    current_company = get_current_company(request)
    if not current_company:
        messages.error(request, 'No company selected. Please select or create a company first.')
        return redirect('core:company_register')
    
    if request.method == 'POST':
        form = ContractorForm(request.POST)
        if form.is_valid():
            contractor = form.save(commit=False)
            contractor.company = current_company
            contractor.created_by = request.user
            contractor.save()
            messages.success(request, f'Contractor "{contractor.name}" created successfully!')
            return redirect('contractors:list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ContractorForm()
    
    return render(request, 'contractors/create.html', {'form': form})

@login_required
def contractor_edit(request, pk):
    """Edit existing contractor"""
    current_company = get_current_company(request)
    contractor = get_object_or_404(Contractor, pk=pk, company=current_company)
    if request.method == 'POST':
        # Add form handling here
        messages.success(request, 'Contractor updated successfully!')
        return redirect('contractors:detail', pk=pk)
    return render(request, 'contractors/edit.html', {'contractor': contractor})

@login_required
def contractor_delete(request, pk):
    """Delete contractor"""
    current_company = get_current_company(request)
    contractor = get_object_or_404(Contractor, pk=pk, company=current_company)
    if request.method == 'POST':
        contractor.is_active = False
        contractor.save()
        messages.success(request, 'Contractor deactivated successfully!')
        return redirect('contractors:list')
    return render(request, 'contractors/delete.html', {'contractor': contractor})
