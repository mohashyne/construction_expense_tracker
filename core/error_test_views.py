"""
Error testing views for Construction Expense Tracker
Provides comprehensive error testing capabilities with categorized error types
"""

from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.exceptions import ValidationError, PermissionDenied
import json
import logging

logger = logging.getLogger(__name__)

def is_staff_or_superuser(user):
    """Check if user is staff or superuser"""
    return user.is_authenticated and (user.is_staff or user.is_superuser)

@login_required
@user_passes_test(is_staff_or_superuser)
def trigger_error(request):
    """
    View to trigger specific categorized errors for testing the error handling system
    Only accessible to staff/superuser accounts
    """
    
    if not settings.DEBUG and not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({
            'error': 'Access denied',
            'message': 'Error testing is only available to administrators'
        }, status=403)
    
    error_type = request.GET.get('type', 'generic')
    
    try:
        # Database Errors (DB-xxxx)
        if error_type == 'database':
            from projects.models import Project
            # This should trigger a database error
            project = Project.objects.get(id=999999999)
            
        elif error_type == 'integrity':
            from core.models import Company
            # Try to create duplicate company with same slug
            Company.objects.create(name='Test Company', slug='duplicate-test')
            Company.objects.create(name='Test Company 2', slug='duplicate-test')
            
        # Authentication & Permission Errors (AU-xxxx)
        elif error_type == 'permission':
            raise PermissionDenied("Access denied to protected construction resource")
            
        elif error_type == 'authentication':
            from django.contrib.auth.models import AnonymousUser
            if isinstance(request.user, AnonymousUser):
                raise Exception("Authentication required")
            # Simulate auth failure
            raise Exception("Authentication failed for construction tracker")
        
        # Validation Errors (VL-xxxx)    
        elif error_type == 'validation':
            raise ValidationError("Invalid project budget: cannot be negative")
            
        elif error_type == 'value':
            # Trigger ValueError with construction context
            budget = float('invalid_budget_amount')
            
        elif error_type == 'type':
            # Trigger TypeError with construction context
            project_cost = "1000" + 500  # String + int
            
        elif error_type == 'attribute':
            # Trigger AttributeError with construction context
            class Project:
                pass
            project = Project()
            total_cost = project.non_existent_budget.calculate()
        
        # Business Logic Errors (BL-xxxx)
        elif error_type == 'company_access':
            raise Exception("CompanyAccessError: User does not have access to this company's projects")
            
        elif error_type == 'insufficient_funds':
            raise Exception("InsufficientFundsError: Project budget exceeded, cannot approve expense")
            
        elif error_type == 'project_budget':
            raise Exception("ProjectBudgetError: Project budget must be greater than current expenses")
            
        elif error_type == 'expense_approval':
            raise Exception("ExpenseApprovalError: Expense cannot be approved without supervisor authorization")
            
        elif error_type == 'contractor_not_found':
            raise Exception("ContractorNotFoundError: Contractor not found in company directory")
        
        # System Errors (SY-xxxx)
        elif error_type == 'import':
            from non_existent_construction_module import calculate_expenses
            
        elif error_type == 'key':
            project_data = {'name': 'Test Project', 'budget': 10000}
            return project_data['non_existent_contractor_key']
            
        elif error_type == 'index':
            expense_list = [100, 200, 300]
            return expense_list[10]
            
        elif error_type == 'file_not_found':
            with open('/construction/reports/non_existent_report.pdf', 'r') as f:
                content = f.read()
                
        elif error_type == 'zero_division':
            total_budget = 10000
            project_count = 0
            average_budget = total_budget / project_count
        
        # Network/External Service Errors (NT-xxxx)
        elif error_type == 'connection':
            import requests
            # Simulate connection error to external service
            response = requests.get('http://non-existent-construction-api.com/projects', timeout=1)
            
        elif error_type == 'timeout':
            import time
            # Simulate timeout in report generation
            time.sleep(30)  # This will likely timeout
            
        # Generic Application Errors (AP-xxxx)
        elif error_type == 'runtime':
            raise RuntimeError("Construction tracker runtime error: Failed to calculate project totals")
            
        elif error_type == 'not_implemented':
            raise NotImplementedError("Advanced reporting feature not yet implemented")
            
        elif error_type == 'generic':
            raise Exception("Generic construction tracker error for testing purposes")
            
        else:
            return JsonResponse({
                'error': 'Unknown error type',
                'available_types': {
                    'database': ['database', 'integrity'],
                    'authentication': ['permission', 'authentication'],
                    'validation': ['validation', 'value', 'type', 'attribute'],
                    'business_logic': ['company_access', 'insufficient_funds', 'project_budget', 'expense_approval', 'contractor_not_found'],
                    'system': ['import', 'key', 'index', 'file_not_found', 'zero_division'],
                    'network': ['connection', 'timeout'],
                    'application': ['runtime', 'not_implemented', 'generic']
                }
            }, status=400)
            
    except Exception as e:
        # This exception should be caught by our error handling middleware
        # and display the detailed error page with categorized error codes
        raise e
    
    # If we reach here, no error was triggered
    return JsonResponse({
        'status': 'No error triggered',
        'error_type': error_type,
        'message': 'The error type may not be implemented or the condition was not met'
    })

@login_required
@user_passes_test(is_staff_or_superuser)
def error_test_panel(request):
    """
    Render a comprehensive test panel for triggering different types of construction errors
    """
    
    if not settings.DEBUG and not (request.user.is_staff or request.user.is_superuser):
        return HttpResponse("Access denied - Admin privileges required", status=403)
    
    context = {
        'error_categories': {
            'Database Errors (DB-xxxx)': [
                {'type': 'database', 'name': 'DatabaseError', 'description': 'Database query fails (missing project)'},
                {'type': 'integrity', 'name': 'IntegrityError', 'description': 'Database constraint violation (duplicate company)'},
            ],
            'Authentication & Permission (AU-xxxx)': [
                {'type': 'permission', 'name': 'PermissionDenied', 'description': 'Access denied to construction resource'},
                {'type': 'authentication', 'name': 'AuthenticationFailed', 'description': 'Authentication failure'},
            ],
            'Validation Errors (VL-xxxx)': [
                {'type': 'validation', 'name': 'ValidationError', 'description': 'Django validation error (invalid budget)'},
                {'type': 'value', 'name': 'ValueError', 'description': 'Invalid value conversion (budget)'},
                {'type': 'type', 'name': 'TypeError', 'description': 'Type mismatch (string + number)'},
                {'type': 'attribute', 'name': 'AttributeError', 'description': 'Missing object attribute'},
            ],
            'Business Logic (BL-xxxx)': [
                {'type': 'company_access', 'name': 'CompanyAccessError', 'description': 'User lacks company project access'},
                {'type': 'insufficient_funds', 'name': 'InsufficientFundsError', 'description': 'Project budget exceeded'},
                {'type': 'project_budget', 'name': 'ProjectBudgetError', 'description': 'Invalid project budget amount'},
                {'type': 'expense_approval', 'name': 'ExpenseApprovalError', 'description': 'Expense approval requirements not met'},
                {'type': 'contractor_not_found', 'name': 'ContractorNotFoundError', 'description': 'Contractor not in company directory'},
            ],
            'System Errors (SY-xxxx)': [
                {'type': 'import', 'name': 'ImportError', 'description': 'Missing module import'},
                {'type': 'key', 'name': 'KeyError', 'description': 'Dictionary key not found'},
                {'type': 'index', 'name': 'IndexError', 'description': 'List index out of range'},
                {'type': 'file_not_found', 'name': 'FileNotFoundError', 'description': 'Report file does not exist'},
                {'type': 'zero_division', 'name': 'ZeroDivisionError', 'description': 'Division by zero in calculations'},
            ],
            'Network/External Services (NT-xxxx)': [
                {'type': 'connection', 'name': 'ConnectionError', 'description': 'External API connection failed'},
                {'type': 'timeout', 'name': 'TimeoutError', 'description': 'Request timeout (simulated)'},
            ],
            'Application Errors (AP-xxxx)': [
                {'type': 'runtime', 'name': 'RuntimeError', 'description': 'Runtime calculation error'},
                {'type': 'not_implemented', 'name': 'NotImplementedError', 'description': 'Feature not implemented'},
                {'type': 'generic', 'name': 'Generic Exception', 'description': 'Generic application error'},
            ],
        },
        'user': request.user,
        'debug_mode': settings.DEBUG
    }
    
    template_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Construction Tracker - Error Testing Panel</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .error-card:hover { 
            transform: translateY(-2px); 
            transition: transform 0.2s; 
        }
        .debug-badge { 
            background: linear-gradient(45deg, #28a745, #20c997); 
        }
        .category-header {
            background: linear-gradient(45deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
        }
        .error-type-badge {
            font-family: 'Courier New', monospace;
            font-weight: bold;
        }
    </style>
</head>
<body class="bg-light">
    <div class="container mt-4">
        <div class="row">
            <div class="col-12">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <div>
                        <h1 class="display-6"><i class="fas fa-hard-hat"></i> Construction Tracker Error Testing</h1>
                        <p class="lead">Comprehensive error handling system testing panel</p>
                    </div>
                    <div>
                        <span class="badge debug-badge fs-6">
                            {% if debug_mode %}DEBUG MODE{% else %}PRODUCTION{% endif %}
                        </span>
                    </div>
                </div>
                
                <div class="alert alert-warning">
                    <h6><i class="fas fa-exclamation-triangle"></i> Administrator Access</h6>
                    <p class="mb-0">
                        Logged in as: <strong>{{ user.username }}</strong> 
                        (Staff: {{ user.is_staff }}, Superuser: {{ user.is_superuser }})
                        <br>This panel tests the categorized error handling system with unique error codes.
                    </p>
                </div>
            </div>
        </div>
        
        {% for category, errors in error_categories.items %}
        <div class="mb-4">
            <div class="category-header p-3 mb-3">
                <h4 class="mb-0">{{ category }}</h4>
            </div>
            
            <div class="row">
                {% for error in errors %}
                <div class="col-lg-6 col-xl-4 mb-3">
                    <div class="card error-card h-100">
                        <div class="card-body">
                            <h5 class="card-title">
                                <span class="badge bg-secondary error-type-badge">{{ error.name }}</span>
                            </h5>
                            <p class="card-text">{{ error.description }}</p>
                            <a href="/core/test-error/?type={{ error.type }}" 
                               class="btn btn-outline-danger btn-sm" 
                               onclick="return confirm('This will trigger a {{ error.name }}. Continue?')">
                                <i class="fas fa-bug"></i> Trigger Error
                            </a>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endfor %}
        
        <div class="row mt-5">
            <div class="col-12">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5><i class="fas fa-info-circle"></i> Error Code System Guide</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h6>Error Code Categories:</h6>
                                <ul class="list-unstyled">
                                    <li><code class="text-danger">DB-xxxx</code> Database Errors</li>
                                    <li><code class="text-warning">AU-xxxx</code> Authentication/Permission</li>
                                    <li><code class="text-info">VL-xxxx</code> Validation Errors</li>
                                    <li><code class="text-success">BL-xxxx</code> Business Logic</li>
                                    <li><code class="text-secondary">SY-xxxx</code> System Errors</li>
                                    <li><code class="text-primary">NT-xxxx</code> Network/External</li>
                                    <li><code class="text-dark">AP-xxxx</code> Application Errors</li>
                                </ul>
                            </div>
                            <div class="col-md-6">
                                <h6>How the System Works:</h6>
                                <ol>
                                    <li>Each error gets a <strong>unique Error ID</strong> (8-char UUID)</li>
                                    <li>Each error gets a <strong>categorized Error Code</strong> (e.g., DB-A1B2)</li>
                                    <li>Errors are classified by <strong>severity</strong> (Critical/High/Medium/Low)</li>
                                    <li>Critical/High errors trigger <strong>email notifications</strong></li>
                                    <li>All errors are <strong>logged</strong> with full context</li>
                                    <li>Company context is captured for multi-tenant errors</li>
                                </ol>
                            </div>
                        </div>
                        
                        <div class="alert alert-info mt-3">
                            <strong>Testing Results:</strong>
                            <br>• Each error will show both Error ID and Error Code
                            <br>• Detailed error pages show company context and severity
                            <br>• AJAX/API errors return JSON with error codes
                            <br>• Add <code>?show_debug=true</code> to see detailed debugging info (staff only)
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row mt-4">
            <div class="col-12 text-center">
                <a href="/dashboard/" class="btn btn-primary">
                    <i class="fas fa-home"></i> Back to Dashboard
                </a>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
    """
    
    from django.template import Template, Context
    template = Template(template_content)
    html_content = template.render(Context(context))
    
    return HttpResponse(html_content)

@csrf_exempt
def error_api_test(request):
    """
    API endpoint to test error handling in AJAX requests with categorized error codes
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body) if request.body else {}
        error_type = data.get('error_type', 'generic')
        
        if error_type == 'validation':
            raise ValidationError("API validation error: Invalid project data")
        elif error_type == 'permission':
            raise PermissionDenied("API permission error: Access denied")
        elif error_type == 'database':
            from projects.models import Project
            project = Project.objects.get(id=999999)
        elif error_type == 'business_logic':
            raise Exception("InsufficientFundsError: API budget validation failed")
        else:
            raise RuntimeError(f"API error type: {error_type}")
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON', 'error_code': 'VL-JSON'}, status=400)
    except Exception as e:
        # This should be caught by middleware and return JSON response with error codes
        raise e
