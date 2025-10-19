from django.shortcuts import render
from django.http import HttpResponseNotFound, HttpResponseServerError, HttpResponseForbidden
from django.utils import timezone
from django.conf import settings
import logging
import uuid

logger = logging.getLogger(__name__)

def custom_404_handler(request, exception):
    """Custom 404 error handler"""
    error_id = str(uuid.uuid4())
    logger.warning(f"404 Error - ID: {error_id}, Path: {request.path}, User: {request.user.id if request.user.is_authenticated else 'Anonymous'}")
    
    context = {
        'error_code': f"404-{error_id[:8]}",
        'timestamp': timezone.now(),
        'path': request.path,
    }
    return render(request, 'errors/404.html', context, status=404)

def custom_500_handler(request):
    """Custom 500 error handler"""
    error_id = str(uuid.uuid4())
    logger.error(f"500 Error - ID: {error_id}, Path: {request.path}, User: {request.user.id if request.user.is_authenticated else 'Anonymous'}")
    
    context = {
        'error_code': f"500-{error_id[:8]}",
        'timestamp': timezone.now(),
        'path': request.path,
    }
    return render(request, 'errors/500.html', context, status=500)

def custom_403_handler(request, exception):
    """Custom 403 error handler"""
    error_id = str(uuid.uuid4())
    logger.warning(f"403 Error - ID: {error_id}, Path: {request.path}, User: {request.user.id if request.user.is_authenticated else 'Anonymous'}")
    
    context = {
        'error_code': f"403-{error_id[:8]}",
        'timestamp': timezone.now(),
        'path': request.path,
    }
    return render(request, 'errors/403.html', context, status=403)

def custom_400_handler(request, exception):
    """Custom 400 error handler"""
    error_id = str(uuid.uuid4())
    logger.warning(f"400 Error - ID: {error_id}, Path: {request.path}, User: {request.user.id if request.user.is_authenticated else 'Anonymous'}")
    
    context = {
        'error_code': f"400-{error_id[:8]}",
        'timestamp': timezone.now(),
        'path': request.path,
        'error_message': 'Bad Request - The server could not understand the request.',
    }
    return render(request, 'errors/400.html', context, status=400)

# Error Code Dictionary for different error types
ERROR_CODES = {
    # Dashboard Errors (DASH)
    'DASH001': 'Dashboard loading error',
    'DASH002': 'Dashboard data processing error',
    
    # Project Errors (PROJ)
    'PROJ001': 'Project list loading error',
    'PROJ002': 'Project detail loading error',
    'PROJ003': 'Project creation error',
    'PROJ004': 'Project update error',
    'PROJ005': 'Project deletion error',
    
    # Expense Errors (EXP)
    'EXP001': 'Expense list loading error',
    'EXP002': 'Expense detail loading error',
    'EXP003': 'Expense creation error',
    'EXP004': 'Expense update error',
    'EXP005': 'Expense deletion error',
    'EXP006': 'Expense approval error',
    
    # Contractor Errors (CONT)
    'CONT001': 'Contractor list loading error',
    'CONT002': 'Contractor detail loading error',
    'CONT003': 'Contractor creation error',
    'CONT004': 'Contractor update error',
    'CONT005': 'Contractor deletion error',
    
    # Company Errors (COMP)
    'COMP001': 'Company registration error',
    'COMP002': 'Company management error',
    'COMP003': 'Company switching error',
    'COMP004': 'Company settings error',
    
    # Role & Permission Errors (ROLE)
    'ROLE001': 'Role creation error',
    'ROLE002': 'Role update error',
    'ROLE003': 'Role deletion error',
    'ROLE004': 'Permission assignment error',
    
    # User Management Errors (USER)
    'USER001': 'User invitation error',
    'USER002': 'User profile error',
    'USER003': 'User authentication error',
    'USER004': 'User authorization error',
    
    # Notification Errors (NOTIF)
    'NOTIF001': 'Notification creation error',
    'NOTIF002': 'Notification delivery error',
    'NOTIF003': 'Notification update error',
    
    # Database Errors (DB)
    'DB001': 'Database connection error',
    'DB002': 'Database query error',
    'DB003': 'Database integrity error',
    
    # File Upload Errors (FILE)
    'FILE001': 'File upload error',
    'FILE002': 'File processing error',
    'FILE003': 'File size exceeded',
    'FILE004': 'Invalid file type',
    
    # API Errors (API)
    'API001': 'API authentication error',
    'API002': 'API rate limit exceeded',
    'API003': 'API data validation error',
    'API004': 'API external service error',
    
    # System Errors (SYS)
    'SYS001': 'System configuration error',
    'SYS002': 'System resource error',
    'SYS003': 'System maintenance mode',
}

class ErrorHandlingMiddleware:
    """
    Middleware for comprehensive error handling and logging
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        """Process unhandled exceptions"""
        error_id = str(uuid.uuid4())
        
        # Log the error with context
        logger.error(
            f"Unhandled Exception - ID: {error_id}, "
            f"Path: {request.path}, "
            f"User: {request.user.id if request.user.is_authenticated else 'Anonymous'}, "
            f"Exception: {type(exception).__name__}: {str(exception)}",
            exc_info=True
        )
        
        # Don't handle the exception in debug mode
        if settings.DEBUG:
            return None
            
        # Return custom 500 response
        context = {
            'error_code': f"500-{error_id[:8]}",
            'timestamp': timezone.now(),
        }
        return render(request, 'errors/500.html', context, status=500)

def get_error_message(error_code):
    """Get human-readable error message for error code"""
    return ERROR_CODES.get(error_code, 'Unknown error occurred')

def log_business_error(error_code, message, user_id=None, extra_data=None):
    """Log business logic errors with structured data"""
    log_data = {
        'error_code': error_code,
        'message': message,
        'user_id': user_id,
        'timestamp': timezone.now().isoformat(),
    }
    
    if extra_data:
        log_data.update(extra_data)
    
    logger.error(f"Business Error - {error_code}: {message}", extra=log_data)
