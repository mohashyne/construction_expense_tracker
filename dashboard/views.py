from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from django.http import Http404
from datetime import datetime, timedelta
from decimal import Decimal
from projects.models import Project
from expenses.models import Expense, ExpenseCategory
from contractors.models import Contractor
from core.views import get_current_company
import logging

logger = logging.getLogger(__name__)

def home(request):
    """Landing page"""
    if request.user.is_authenticated:
        # Check if user is a super owner - redirect to super owner dashboard
        try:
            if hasattr(request.user, 'userprofile') and request.user.userprofile.is_super_owner():
                return redirect('super_owner:dashboard')
        except:
            pass
        return redirect('dashboard:dashboard')
    return render(request, 'dashboard/home.html')

@login_required
def dashboard(request):
    """Main dashboard with KPIs and charts"""
    try:
        user = request.user
        
        # Check if user is a super owner - redirect to super owner dashboard
        try:
            if hasattr(user, 'userprofile') and user.userprofile.is_super_owner():
                return redirect('super_owner:dashboard')
        except:
            pass
        
        current_company = get_current_company(request)
        
        if not current_company:
            messages.warning(request, 'Please select a company or register one to continue.')
            return redirect('core:company_register')
        
        # Get date range for filtering (default to last 30 days)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        # Basic KPIs - Updated for multi-tenant structure
        total_projects = Project.objects.filter(company=current_company).count()
        active_projects = Project.objects.filter(
            company=current_company, 
            status__in=['planning', 'in_progress']
        ).count()
        completed_projects = Project.objects.filter(
            company=current_company, 
            status='completed'
        ).count()
        overdue_projects = Project.objects.filter(
            company=current_company,
            expected_completion_date__lt=end_date,
            status__in=['planning', 'in_progress']
        ).count()
        
        # Financial KPIs
        total_budget = Project.objects.filter(company=current_company).aggregate(
            total=Sum('total_budget')
        )['total'] or Decimal('0.00')
        
        total_expenses = Expense.objects.filter(
            project__company=current_company
        ).aggregate(
            total=Sum('actual_cost')
        )['total'] or Decimal('0.00')
        
        total_planned_expenses = Expense.objects.filter(
            project__company=current_company
        ).aggregate(
            total=Sum('planned_cost')
        )['total'] or Decimal('0.00')
        
        budget_variance = total_budget - total_expenses
        budget_utilization = (total_expenses / total_budget * 100) if total_budget > 0 else 0
        
        # Recent projects
        recent_projects = Project.objects.filter(company=current_company).order_by('-created_at')[:5]
        
        # Recent expenses
        recent_expenses = Expense.objects.filter(
            project__company=current_company
        ).select_related('project').order_by('-expense_date')[:5]
        
        # Projects by status (for chart)
        projects_by_status = Project.objects.filter(company=current_company).values('status').annotate(
            count=Count('id')
        )
        
        # Monthly expense trend (last 6 months)
        monthly_expenses = []
        for i in range(6):
            month_start = (end_date.replace(day=1) - timedelta(days=i*30)).replace(day=1)
            month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            
            month_total = Expense.objects.filter(
                project__company=current_company,
                expense_date__range=[month_start, month_end]
            ).aggregate(total=Sum('actual_cost'))['total'] or Decimal('0.00')
            
            monthly_expenses.append({
                'month': month_start.strftime('%b %Y'),
                'total': float(month_total)
            })
        
        monthly_expenses.reverse()
        
        # Expenses by category (for pie chart)
        expenses_by_category = Expense.objects.filter(
            project__company=current_company
        ).exclude(
            category__isnull=True
        ).values('category__name', 'category__color').annotate(
            total=Sum('actual_cost')
        )
        
        context = {
            'current_company': current_company,
            'total_projects': total_projects,
            'active_projects': active_projects,
            'completed_projects': completed_projects,
            'overdue_projects': overdue_projects,
            'total_budget': total_budget,
            'total_expenses': total_expenses,
            'total_planned_expenses': total_planned_expenses,
            'budget_variance': budget_variance,
            'budget_utilization': round(budget_utilization, 1),
            'recent_projects': recent_projects,
            'recent_expenses': recent_expenses,
            'projects_by_status': list(projects_by_status),
            'monthly_expenses': monthly_expenses,
            'expenses_by_category': list(expenses_by_category),
        }
        
        return render(request, 'dashboard/dashboard.html', context)
        
    except Exception as e:
        logger.error(f'Dashboard error for user {user.id}: {str(e)}', exc_info=True)
        messages.error(request, 'An error occurred while loading the dashboard. Please try again.')
        return render(request, 'errors/500.html', {'error_code': 'DASH001'}, status=500)
