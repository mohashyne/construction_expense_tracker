"""
URL configuration for construction_tracker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path('', include('dashboard.urls')),
    path('', include('core.urls')),
    path('projects/', include('projects.urls')),
    path('expenses/', include('expenses.urls')),
    path('contractors/', include('contractors.urls')),
    # Super Owner Management System
    path('super-owner/', include('core.super_owner_urls')),
]

# Error handlers
handler404 = 'core.error_handlers.custom_404_handler'
handler500 = 'core.error_handlers.custom_500_handler'
handler403 = 'core.error_handlers.custom_403_handler'
handler400 = 'core.error_handlers.custom_400_handler'

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
