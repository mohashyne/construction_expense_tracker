from django.urls import path
from . import views

app_name = 'contractors'

urlpatterns = [
    path('', views.contractor_list, name='list'),
    path('create/', views.contractor_create, name='create'),
    path('<int:pk>/', views.contractor_detail, name='detail'),
    path('<int:pk>/edit/', views.contractor_edit, name='edit'),
    path('<int:pk>/delete/', views.contractor_delete, name='delete'),
]
