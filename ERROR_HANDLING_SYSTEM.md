# Construction Expense Tracker - Error Handling System

## Overview

The Construction Expense Tracker features a comprehensive error handling system with unique error codes, categorized error types, and advanced debugging capabilities. This system is based on the successful implementation from Cavendish Auto Services but enhanced for construction industry use cases.

## Features

### 🏷️ Categorized Error Codes
Each error receives a unique categorized code for easy identification:

- **DB-xxxx**: Database Errors (IntegrityError, DatabaseError, etc.)
- **AU-xxxx**: Authentication & Permission Errors
- **VL-xxxx**: Validation Errors (ValueError, ValidationError, etc.)
- **BL-xxxx**: Business Logic Errors (specific to construction operations)
- **SY-xxxx**: System Errors (ImportError, KeyError, etc.)
- **NT-xxxx**: Network/External Service Errors
- **AP-xxxx**: Generic Application Errors

### 🆔 Unique Error Tracking
- **Error ID**: 8-character UUID for tracking specific error instances
- **Error Code**: Category prefix + 4-character hash for error type classification

### 📊 Severity Classification
Errors are automatically classified by severity:
- **Critical**: Database errors, integrity violations
- **High**: Permission errors, validation failures
- **Medium**: Type errors, attribute errors
- **Low**: Generic application errors

### 🏢 Multi-Tenant Context
The system captures company context for multi-tenant environments:
- Current company information
- User role and permissions
- Company-specific error patterns

## Components

### 1. Error Middleware (`core/error_middleware.py`)
The main error handling middleware that:
- Intercepts all exceptions
- Generates unique error IDs and categorized error codes
- Logs errors with appropriate severity levels
- Sends email notifications for critical/high severity errors
- Renders detailed error pages for debugging
- Provides user-friendly error pages for end users
- Returns JSON responses for API/AJAX requests

### 2. Error Testing System (`core/error_test_views.py`)
Comprehensive testing interface that allows administrators to:
- Trigger specific error types for testing
- Verify error handling behavior
- Test categorized error codes
- Validate email notifications
- Check logging functionality

### 3. Error Templates
- **Detailed Error Page**: For developers/administrators with full debugging info
- **User-Friendly Error Page**: Clean interface for end users
- **API Error Responses**: JSON format with error codes for programmatic handling

## Configuration

### Settings Variables
Add these to your `.env` file:

```env
# Email configuration for error notifications
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@constructiontracker.com

# Admin emails for error notifications (comma-separated)
ADMIN_EMAILS=admin@constructiontracker.com,dev@constructiontracker.com
```

### Middleware Setup
The middleware is automatically configured in `settings.py`:
```python
MIDDLEWARE = [
    # ... other middleware ...
    "core.error_middleware.ConstructionErrorHandlerMiddleware",
    # ... rest of middleware ...
]
```

## Usage

### Testing the Error System
1. Navigate to `/core/test-errors/` (admin/staff only)
2. Choose from categorized error types
3. Trigger errors to test the system
4. Verify error codes, notifications, and logging

### Understanding Error Codes
When an error occurs, you'll see:
- **Error ID**: `A1B2C3D4` (unique instance identifier)
- **Error Code**: `DB-5F2A` (category + type identifier)

Example error codes:
- `DB-A1B2`: Database integrity constraint violation
- `AU-C3D4`: Permission denied error
- `VL-E5F6`: Form validation error
- `BL-G7H8`: Business logic error (e.g., insufficient funds)

### API Error Responses
API endpoints return structured error information:
```json
{
  "error": true,
  "error_code": "BL-A1B2",
  "error_id": "C3D4E5F6",
  "message": "An error occurred while processing your request",
  "details": "Project budget exceeded",
  "timestamp": "2023-10-18T10:30:00Z",
  "severity": "high"
}
```

### Debug Mode
Add `?show_debug=true` to any URL (staff only) to see detailed error information in production.

## Error Categories in Detail

### Database Errors (DB-xxxx)
- **DB-xxxx**: General database connectivity issues
- **Integrity violations**: Unique constraint failures, foreign key errors
- **Query errors**: Malformed queries, missing tables

### Authentication & Permission (AU-xxxx)
- **AU-xxxx**: Login failures, session timeouts
- **Permission denied**: Insufficient privileges for company resources
- **Multi-tenant access**: Cross-company data access attempts

### Validation Errors (VL-xxxx)
- **Form validation**: Invalid form data submission
- **Data type errors**: String/number conversion failures
- **Business rule validation**: Negative budgets, invalid dates

### Business Logic (BL-xxxx)
Construction-specific business errors:
- **Company access**: User lacks access to company projects
- **Budget validation**: Project budget constraints
- **Expense approval**: Approval workflow violations
- **Contractor management**: Contractor directory errors

### System Errors (SY-xxxx)
- **Import errors**: Missing modules or dependencies
- **File system**: Missing files, permission issues
- **Memory/resource**: Out of memory, disk space issues

### Network/External (NT-xxxx)
- **API connections**: External service failures
- **Timeout errors**: Long-running operations
- **Service unavailable**: Third-party service outages

## Monitoring and Maintenance

### Log Analysis
Errors are logged to the application logs with severity levels:
```
[CRITICAL] [DB-A1B2] DatabaseError: Connection timeout
[ERROR] [AU-C3D4] PermissionDenied: Access denied to project
[WARNING] [VL-E5F6] ValueError: Invalid budget amount
```

### Email Notifications
Critical and high-severity errors automatically send detailed email notifications to administrators with:
- Error code and ID
- Full stack trace
- Request information
- User and company context
- Environment details

### Error Trends
Monitor error patterns by:
- **Error codes**: Track recurring error types
- **Company context**: Identify company-specific issues
- **User patterns**: Detect user behavior issues
- **Time patterns**: Identify peak error periods

## Best Practices

### For Developers
1. **Use specific exceptions** for business logic errors
2. **Include context** in error messages (company, project, etc.)
3. **Log before raising** custom exceptions for debugging
4. **Test error scenarios** using the error testing panel

### For System Administrators
1. **Monitor email notifications** for critical errors
2. **Review error logs regularly** for patterns
3. **Set up log rotation** to prevent disk space issues
4. **Configure proper email settings** for notifications

### For Support Teams
1. **Reference error codes** when investigating issues
2. **Use error IDs** to track specific user problems
3. **Check company context** for multi-tenant issues
4. **Escalate based on severity** levels

## Troubleshooting

### Common Issues

**Middleware not working:**
- Check middleware order in `settings.py`
- Verify middleware class name is correct
- Check for conflicting middleware

**Email notifications not sending:**
- Verify email settings in `.env`
- Check `ADMIN_EMAILS` configuration
- Test email backend connectivity

**Error codes not showing:**
- Ensure middleware is active
- Check exception handling in views
- Verify error code generation logic

**Debug pages not appearing:**
- Check user permissions (staff/superuser required)
- Verify `show_debug=true` parameter
- Check Django DEBUG setting

This error handling system provides comprehensive error tracking and debugging capabilities while maintaining a user-friendly experience for end users.
