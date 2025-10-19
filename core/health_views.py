"""
Health check views for production monitoring
"""
import json
import time
from django.http import JsonResponse
from django.db import connection, DatabaseError
from django.core.cache import cache
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache


@never_cache
@require_http_methods(["GET"])
def health_check(request):
    """
    Basic health check endpoint
    Returns 200 if the application is running
    """
    return JsonResponse({
        'status': 'healthy',
        'timestamp': time.time()
    })


@never_cache
@require_http_methods(["GET"])
def detailed_health_check(request):
    """
    Detailed health check that tests database, cache, etc.
    """
    health_data = {
        'status': 'healthy',
        'timestamp': time.time(),
        'checks': {}
    }
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_data['checks']['database'] = 'healthy'
    except DatabaseError as e:
        health_data['status'] = 'unhealthy'
        health_data['checks']['database'] = f'unhealthy: {str(e)}'
    
    # Cache check
    try:
        test_key = 'health_check_test'
        test_value = 'test_value'
        cache.set(test_key, test_value, 10)
        cached_value = cache.get(test_key)
        if cached_value == test_value:
            health_data['checks']['cache'] = 'healthy'
        else:
            health_data['checks']['cache'] = 'unhealthy: cache not working'
            health_data['status'] = 'unhealthy'
    except Exception as e:
        health_data['status'] = 'unhealthy'
        health_data['checks']['cache'] = f'unhealthy: {str(e)}'
    
    # Return appropriate status code
    status_code = 200 if health_data['status'] == 'healthy' else 503
    return JsonResponse(health_data, status=status_code)


@never_cache
@require_http_methods(["GET"])
def readiness_check(request):
    """
    Readiness check for Kubernetes/Docker deployments
    """
    return JsonResponse({
        'status': 'ready',
        'timestamp': time.time()
    })


@never_cache
@require_http_methods(["GET"])
def liveness_check(request):
    """
    Liveness check for Kubernetes/Docker deployments
    """
    return JsonResponse({
        'status': 'alive',
        'timestamp': time.time()
    })
