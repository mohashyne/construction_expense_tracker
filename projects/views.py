from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Project, ProjectContractor
from .forms import ProjectForm, ProjectContractorForm, ProjectFilterForm
from core.views import get_current_company
import logging

logger = logging.getLogger(__name__)

@login_required
def project_list(request):
    """List all projects for the current company with filtering and search"""
    try:
        current_company = get_current_company(request)
        if not current_company:
            messages.warning(request, 'Please select a company to view projects.')
            return redirect('core:company_register')
            
        projects = Project.objects.filter(company=current_company).order_by('-created_at')
        
        # Handle search and filtering
        search = request.GET.get('search')
        status = request.GET.get('status')
        priority = request.GET.get('priority')
        date_from = request.GET.get('date_from')
        
        if search:
            projects = projects.filter(
                Q(name__icontains=search) | 
                Q(location__icontains=search) |
                Q(client_name__icontains=search) |
                Q(description__icontains=search)
            )
        
        if status:
            projects = projects.filter(status=status)
        
        if priority:
            projects = projects.filter(priority=priority)
        
        if date_from:
            projects = projects.filter(start_date__gte=date_from)
    
        # Pagination
        paginator = Paginator(projects, 10)  # Show 10 projects per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'projects': page_obj,
            'filter_form': ProjectFilterForm(request.GET),
            'current_company': current_company,
        }
        return render(request, 'projects/list.html', context)
        
    except Exception as e:
        logger.error(f'Project list error for user {request.user.id}: {str(e)}', exc_info=True)
        messages.error(request, 'An error occurred while loading projects. Please try again.')
        return render(request, 'errors/500.html', {'error_code': 'PROJ001'}, status=500)

@login_required
def project_detail(request, pk):
    """Project detail view with expenses and contractors"""
    try:
        current_company = get_current_company(request)
        if not current_company:
            messages.warning(request, 'Please select a company to view projects.')
            return redirect('core:company_register')
            
        project = get_object_or_404(Project, pk=pk, company=current_company)
        project_contractors = ProjectContractor.objects.filter(project=project)
        recent_expenses = project.expenses.order_by('-expense_date')[:10]
        
        context = {
            'project': project,
            'project_contractors': project_contractors,
            'recent_expenses': recent_expenses,
            'current_company': current_company,
        }
        return render(request, 'projects/detail.html', context)
        
    except Exception as e:
        logger.error(f'Project detail error for user {request.user.id}, project {pk}: {str(e)}', exc_info=True)
        messages.error(request, 'An error occurred while loading the project. Please try again.')
        return render(request, 'errors/500.html', {'error_code': 'PROJ002'}, status=500)

@login_required
def project_create(request):
    """Create new project"""
    if request.method == 'POST':
        form = ProjectForm(user=request.user, data=request.POST, files=request.FILES)
        if form.is_valid():
            project = form.save()
            messages.success(request, f'Project "{project.name}" created successfully!')
            return redirect('projects:detail', pk=project.pk)
    else:
        form = ProjectForm(user=request.user)
    
    return render(request, 'projects/create.html', {'form': form})

@login_required
def project_edit(request, pk):
    """Edit existing project"""
    project = get_object_or_404(Project, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = ProjectForm(user=request.user, data=request.POST, files=request.FILES, instance=project)
        if form.is_valid():
            project = form.save()
            messages.success(request, f'Project "{project.name}" updated successfully!')
            return redirect('projects:detail', pk=project.pk)
    else:
        form = ProjectForm(user=request.user, instance=project)
    
    return render(request, 'projects/edit.html', {'form': form, 'project': project})

@login_required
def project_delete(request, pk):
    """Delete project"""
    project = get_object_or_404(Project, pk=pk, user=request.user)
    
    if request.method == 'POST':
        project_name = project.name
        project.delete()
        messages.success(request, f'Project "{project_name}" deleted successfully!')
        return redirect('projects:list')
    
    return render(request, 'projects/delete.html', {'project': project})
