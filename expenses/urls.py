from django.urls import path
from . import views

app_name = 'expenses'

urlpatterns = [
    path('', views.expense_list, name='list'),
    path('create/', views.expense_create, name='create'),
    path('<int:pk>/', views.expense_detail, name='detail'),
    path('<int:pk>/edit/', views.expense_edit, name='edit'),
    path('<int:pk>/delete/', views.expense_delete, name='delete'),
    path('categories/', views.category_list, name='categories'),
]
