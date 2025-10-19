"""
Enhanced error handling middleware for Construction Expense Tracker
Provides unique error codes for different error types and comprehensive error tracking
"""

import traceback
import sys
import logging
import os
import uuid
import hashlib
from datetime import datetime
from django.http import HttpResponse, JsonResponse
from django.template import Template, Context
from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail
from django.db import DatabaseError, IntegrityError
from django.core.exceptions import ValidationError, PermissionDenied, ObjectDoesNotExist

logger = logging.getLogger(__name__)

class ConstructionErrorHandlerMiddleware:
    """
    Advanced error handling middleware with categorized error codes
    """
    
    # Error code prefixes for different categories
    ERROR_CODES = {
        # Database Errors (DB-xxxx)
        'DatabaseError': 'DB',
        'IntegrityError': 'DB', 
        'OperationalError': 'DB',
        'DataError': 'DB',
        'InternalError': 'DB',
        'ProgrammingError': 'DB',
        
        # Authentication & Permission Errors (AU-xxxx)
        'PermissionDenied': 'AU',
        'AuthenticationFailed': 'AU',
        'Forbidden': 'AU',
        'NotAuthenticated': 'AU',
        
        # Validation Errors (VL-xxxx)
        'ValidationError': 'VL',
        'ValueError': 'VL',
        'TypeError': 'VL',
        'AttributeError': 'VL',
        
        # Business Logic Errors (BL-xxxx)
        'CompanyAccessError': 'BL',
        'InsufficientFundsError': 'BL',
        'ProjectBudgetError': 'BL',
        'ExpenseApprovalError': 'BL',
        'ContractorNotFoundError': 'BL',
        
        # System Errors (SY-xxxx)
        'ImportError': 'SY',
        'KeyError': 'SY',
        'IndexError': 'SY',
        'FileNotFoundError': 'SY',
        'IOError': 'SY',
        'OSError': 'SY',
        
        # Network/External Service Errors (NT-xxxx)
        'ConnectionError': 'NT',
        'TimeoutError': 'NT',
        'HTTPError': 'NT',
        'URLError': 'NT',
        
        # Generic Application Errors (AP-xxxx)
        'Exception': 'AP',
        'RuntimeError': 'AP',
        'NotImplementedError': 'AP',
    }
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        """
        Process exceptions and provide detailed error information with unique codes
        """
        
        # Get detailed error information
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        # Generate unique error ID and categorized error code
        error_id = self.generate_error_id()
        error_code = self.generate_error_code(exception)
        
        error_details = {
            'error_id': error_id,
            'error_code': error_code,
            'timestamp': timezone.now().isoformat(),
            'exception_type': exc_type.__name__ if exc_type else 'Unknown',
            'exception_message': str(exc_value),
            'request_path': request.path,
            'request_method': request.method,
            'user': str(request.user) if hasattr(request, 'user') and request.user.is_authenticated else 'Anonymous',
            'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown'),
            'ip_address': self.get_client_ip(request),
            'post_data': self.sanitize_post_data(dict(request.POST)) if request.method == 'POST' else {},
            'get_data': dict(request.GET) if request.GET else {},
            'session_data': self.sanitize_session_data(dict(request.session)) if hasattr(request, 'session') else {},
            'traceback': traceback.format_exc(),
            'environment': self.get_environment(),
            'python_version': sys.version,
            'django_version': getattr(settings, 'DJANGO_VERSION', 'Unknown'),
            'company_context': self.get_company_context(request),
            'severity': self.determine_error_severity(exception),
        }
        
        # Log the error with appropriate level
        self.log_error(error_details)
        
        # Send notification for critical errors
        if error_details['severity'] in ['critical', 'high']:
            try:
                self.send_error_notification(error_details)
            except Exception as email_error:
                logger.error(f"Failed to send error notification: {email_error}")
        
        # Return appropriate response based on request type and user permissions
        return self.render_error_response(request, error_details)
    
    def generate_error_id(self):
        """Generate a unique error ID"""
        return str(uuid.uuid4())[:8].upper()
    
    def generate_error_code(self, exception):
        """Generate a categorized error code based on exception type"""
        exception_name = exception.__class__.__name__
        prefix = self.ERROR_CODES.get(exception_name, 'AP')  # Default to Application error
        
        # Generate a unique 4-digit suffix based on exception details
        error_string = f"{exception_name}{str(exception)}{datetime.now().microsecond}"
        suffix = hashlib.md5(error_string.encode()).hexdigest()[:4].upper()
        
        return f"{prefix}-{suffix}"
    
    def get_client_ip(self, request):
        """Get the client's IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'Unknown')
        return ip
    
    def get_environment(self):
        """Determine the current environment"""
        if settings.DEBUG:
            return 'Development'
        elif 'RENDER' in os.environ:
            return 'Production (Render)'
        elif 'HEROKU' in os.environ:
            return 'Production (Heroku)'
        else:
            return 'Production'
    
    def get_company_context(self, request):
        """Get current company context if available"""
        try:
            if hasattr(request, 'user') and request.user.is_authenticated:
                from .models import UserProfile
                profile = UserProfile.objects.get(user=request.user)
                if profile.last_company:
                    return {
                        'company_id': str(profile.last_company.id),
                        'company_name': profile.last_company.name,
                    }
        except:
            pass
        return None
    
    def determine_error_severity(self, exception):
        """Determine error severity based on exception type"""
        critical_errors = [DatabaseError, IntegrityError]
        high_errors = [PermissionDenied, ValidationError]
        medium_errors = [ValueError, TypeError, AttributeError]
        
        if any(isinstance(exception, error_type) for error_type in critical_errors):
            return 'critical'
        elif any(isinstance(exception, error_type) for error_type in high_errors):
            return 'high'
        elif any(isinstance(exception, error_type) for error_type in medium_errors):
            return 'medium'
        else:
            return 'low'
    
    def sanitize_post_data(self, post_data):
        """Remove sensitive data from POST data"""
        sensitive_fields = ['password', 'password1', 'password2', 'csrfmiddlewaretoken', 
                           'api_key', 'secret', 'token', 'admin_password', 'admin_password_confirm']
        
        sanitized = post_data.copy()
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[field] = ['***REDACTED***']
        return sanitized
    
    def sanitize_session_data(self, session_data):
        """Remove sensitive data from session data"""
        sensitive_keys = ['_auth_user_id', '_auth_user_backend', 'invitation_token']
        
        sanitized = {}
        for key, value in session_data.items():
            if key in sensitive_keys:
                sanitized[key] = '***REDACTED***'
            else:
                sanitized[key] = value
        return sanitized
    
    def log_error(self, error_details):
        """Log error with appropriate severity level"""
        severity = error_details['severity']
        error_msg = f"[{error_details['error_code']}] {error_details['exception_type']}: {error_details['exception_message']}"
        context_msg = f"Request: {error_details['request_method']} {error_details['request_path']} | User: {error_details['user']}"
        
        if severity == 'critical':
            logger.critical(f"{error_msg} | {context_msg}")
            logger.critical(f"Traceback:\n{error_details['traceback']}")
        elif severity == 'high':
            logger.error(f"{error_msg} | {context_msg}")
        elif severity == 'medium':
            logger.warning(f"{error_msg} | {context_msg}")
        else:
            logger.info(f"{error_msg} | {context_msg}")
    
    def should_show_debug_info(self, request):
        """Determine if detailed debug info should be shown"""
        # Show debug info if:
        # 1. DEBUG is True
        # 2. User is superuser/staff
        # 3. Request has special debug parameter
        
        if settings.DEBUG:
            return True
        
        if hasattr(request, 'user') and request.user.is_authenticated:
            if request.user.is_superuser or request.user.is_staff:
                return True
        
        # Allow debug via URL parameter (only for staff)
        if (request.GET.get('show_debug') == 'true' and 
            hasattr(request, 'user') and 
            request.user.is_authenticated and 
            request.user.is_staff):
            return True
        
        return False
    
    def render_error_response(self, request, error_details):
        """Render appropriate error response based on request type"""
        # For API/AJAX requests, return JSON
        if (request.headers.get('Accept', '').startswith('application/json') or 
            request.path.startswith('/api/') or
            request.headers.get('X-Requested-With') == 'XMLHttpRequest'):
            
            return JsonResponse({
                'error': True,
                'error_code': error_details['error_code'],
                'error_id': error_details['error_id'],
                'message': 'An error occurred while processing your request',
                'details': error_details['exception_message'] if self.should_show_debug_info(request) else 'Internal server error',
                'timestamp': error_details['timestamp'],
                'severity': error_details['severity']
            }, status=500)
        
        # For regular requests
        if self.should_show_debug_info(request):
            return self.render_detailed_error_page(error_details)
        else:
            return self.render_user_friendly_error_page(error_details)
    
    def send_error_notification(self, error_details):
        """Send email notification for critical errors"""
        try:
            if not getattr(settings, 'EMAIL_HOST', None):
                return  # No email configuration
            
            subject = f"🚨 Construction Tracker Error [{error_details['error_code']}] - {error_details['exception_type']}"
            
            message = f"""
CRITICAL ERROR ALERT - Construction Expense Tracker

🚨 ERROR DETAILS:
   • Error Code: {error_details['error_code']}
   • Error ID: {error_details['error_id']}
   • Type: {error_details['exception_type']}
   • Message: {error_details['exception_message']}
   • Severity: {error_details['severity'].upper()}
   • Time: {error_details['timestamp']}

🌍 REQUEST INFORMATION:
   • Path: {error_details['request_path']}
   • Method: {error_details['request_method']}
   • User: {error_details['user']}
   • IP: {error_details['ip_address']}
   • Environment: {error_details['environment']}

🏢 COMPANY CONTEXT:
   • Company: {error_details['company_context']['company_name'] if error_details['company_context'] else 'None'}

📊 REQUEST DATA:
   • POST Data: {error_details['post_data']}
   • GET Data: {error_details['get_data']}

🔍 TECHNICAL DETAILS:
   • Python: {error_details['python_version']}
   • User Agent: {error_details['user_agent']}

📄 STACK TRACE:
{error_details['traceback']}

This error occurred in the Construction Expense Tracker system.
Please investigate and resolve as soon as possible.

Error Code: {error_details['error_code']}
Error ID: {error_details['error_id']}
Timestamp: {error_details['timestamp']}
            """
            
            # Send to admin emails from settings
            admin_emails = getattr(settings, 'ADMIN_EMAILS', ['admin@constructiontracker.com'])
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                admin_emails,
                fail_silently=True
            )
            
        except Exception as e:
            logger.error(f"Failed to send error notification email: {e}")
    
    def render_detailed_error_page(self, error_details):
        """Render a detailed error page for debugging"""
        
        template_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚨 System Error - ConstructPro</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .error-header { background: linear-gradient(135deg, #dc3545, #c82333); }
        .error-section { border-left: 4px solid #dc3545; }
        .code-block { 
            background: #f8f9fa; 
            border: 1px solid #dee2e6; 
            font-family: 'Courier New', monospace; 
            font-size: 0.85em;
        }
        .error-id { background: #fff3cd; border: 1px solid #ffeaa7; }
        .severity-critical { background: #f8d7da; border-color: #f5c6cb; color: #721c24; }
        .severity-high { background: #ffeaa7; border-color: #fdd835; color: #856404; }
        .severity-medium { background: #d1ecf1; border-color: #bee5eb; color: #0c5460; }
        .severity-low { background: #d4edda; border-color: #c3e6cb; color: #155724; }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <div class="col-12 error-header text-white p-4 mb-4">
                <h1><i class="fas fa-hard-hat"></i> Construction Tracker - System Error</h1>
                <p class="lead mb-0">Detailed Error Information for Debugging</p>
            </div>
        </div>
        
        <div class="container">
            <div class="row mb-4">
                <div class="col-12">
                    <div class="alert error-id">
                        <div class="row">
                            <div class="col-md-6">
                                <h4><i class="fas fa-id-badge"></i> Error ID: {{ error_id }}</h4>
                            </div>
                            <div class="col-md-6">
                                <h4><i class="fas fa-barcode"></i> Error Code: {{ error_code }}</h4>
                            </div>
                        </div>
                        <div class="row mt-2">
                            <div class="col-12">
                                <span class="badge severity-{{ severity }} fs-6">
                                    Severity: {{ severity|upper }}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-lg-6 mb-4">
                    <div class="card error-section">
                        <div class="card-header bg-danger text-white">
                            <h5><i class="fas fa-exclamation-triangle"></i> Exception Details</h5>
                        </div>
                        <div class="card-body">
                            <table class="table table-sm">
                                <tr><th>Type:</th><td><code>{{ exception_type }}</code></td></tr>
                                <tr><th>Message:</th><td>{{ exception_message }}</td></tr>
                                <tr><th>Timestamp:</th><td>{{ timestamp }}</td></tr>
                                <tr><th>Environment:</th><td><span class="badge bg-warning">{{ environment }}</span></td></tr>
                            </table>
                        </div>
                    </div>
                </div>
                
                <div class="col-lg-6 mb-4">
                    <div class="card error-section">
                        <div class="card-header bg-info text-white">
                            <h5><i class="fas fa-globe"></i> Request Information</h5>
                        </div>
                        <div class="card-body">
                            <table class="table table-sm">
                                <tr><th>Path:</th><td><code>{{ request_path }}</code></td></tr>
                                <tr><th>Method:</th><td><span class="badge bg-primary">{{ request_method }}</span></td></tr>
                                <tr><th>User:</th><td>{{ user }}</td></tr>
                                <tr><th>IP Address:</th><td>{{ ip_address }}</td></tr>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            
            {% if company_context %}
            <div class="row mb-4">
                <div class="col-12">
                    <div class="card error-section">
                        <div class="card-header bg-success text-white">
                            <h5><i class="fas fa-building"></i> Company Context</h5>
                        </div>
                        <div class="card-body">
                            <table class="table table-sm">
                                <tr><th>Company:</th><td>{{ company_context.company_name }}</td></tr>
                                <tr><th>Company ID:</th><td><code>{{ company_context.company_id }}</code></td></tr>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            {% endif %}
            
            {% if post_data %}
            <div class="row mb-4">
                <div class="col-12">
                    <div class="card error-section">
                        <div class="card-header bg-warning text-dark">
                            <h5><i class="fas fa-clipboard-list"></i> Form Data</h5>
                        </div>
                        <div class="card-body">
                            <pre class="code-block p-3">{{ post_data }}</pre>
                        </div>
                    </div>
                </div>
            </div>
            {% endif %}
            
            <div class="row mb-4">
                <div class="col-12">
                    <div class="card error-section">
                        <div class="card-header bg-dark text-white">
                            <h5><i class="fas fa-bug"></i> Stack Trace</h5>
                        </div>
                        <div class="card-body">
                            <pre class="code-block p-3" style="max-height: 400px; overflow-y: auto;">{{ traceback }}</pre>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row mb-4">
                <div class="col-12">
                    <div class="alert alert-info">
                        <h6><i class="fas fa-lightbulb"></i> Error Handling Guide:</h6>
                        <ol class="mb-0">
                            <li><strong>Error Code:</strong> {{ error_code }} - Use this for categorization</li>
                            <li><strong>Error ID:</strong> {{ error_id }} - Use this for tracking specific instances</li>
                            <li>Check the severity level: <strong>{{ severity|upper }}</strong></li>
                            <li>Review the stack trace for the exact line causing the issue</li>
                            <li>Email notification sent to administrators for critical/high severity errors</li>
                            <li>Error details logged to application logs</li>
                        </ol>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
        """
        
        template = Template(template_content)
        context = Context(error_details)
        
        return HttpResponse(template.render(context), status=500)
    
    def render_user_friendly_error_page(self, error_details):
        """Render a user-friendly error page"""
        
        template_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Something went wrong - ConstructPro</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .error-container {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .error-card {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        }
        .severity-critical { color: #dc3545; }
        .severity-high { color: #fd7e14; }
        .severity-medium { color: #ffc107; }
        .severity-low { color: #28a745; }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="container">
            <div class="row justify-content-center">
                <div class="col-lg-8">
                    <div class="error-card p-5 text-center">
                        <div class="mb-4">
                            <i class="fas fa-hard-hat" style="font-size: 4rem; color: #6c757d;"></i>
                        </div>
                        
                        <h1 class="display-4 mb-4">Oops! Something went wrong</h1>
                        <p class="lead">We're sorry, but there was an error processing your request in the Construction Tracker system.</p>
                        
                        <div class="alert alert-light border">
                            <div class="row">
                                <div class="col-md-6">
                                    <h6><i class="fas fa-barcode"></i> Error Code</h6>
                                    <strong>{{ error_code }}</strong>
                                </div>
                                <div class="col-md-6">
                                    <h6><i class="fas fa-id-badge"></i> Error ID</h6>
                                    <strong>{{ error_id }}</strong>
                                </div>
                            </div>
                            <div class="row mt-3">
                                <div class="col-12">
                                    <span class="badge severity-{{ severity }} fs-6">
                                        Priority: {{ severity|upper }}
                                    </span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="mt-4">
                            <a href="javascript:history.back()" class="btn btn-primary me-2">
                                <i class="fas fa-arrow-left"></i> Go Back
                            </a>
                            <a href="/" class="btn btn-outline-secondary">
                                <i class="fas fa-home"></i> Dashboard
                            </a>
                        </div>
                        
                        <div class="mt-4">
                            <p class="text-muted">
                                {% if severity == 'critical' or severity == 'high' %}
                                The development team has been automatically notified about this {{ severity }} priority error.<br>
                                {% endif %}
                                If you need immediate assistance, please contact support and reference:<br>
                                <strong>Error Code: {{ error_code }}</strong> | <strong>Error ID: {{ error_id }}</strong>
                            </p>
                        </div>
                        
                        {% if company_context %}
                        <div class="mt-3">
                            <small class="text-muted">
                                Company: {{ company_context.company_name }}
                            </small>
                        </div>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
        """
        
        template = Template(template_content)
        context = Context(error_details)
        
        return HttpResponse(template.render(context), status=500)
