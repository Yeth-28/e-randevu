from django.urls import path
from . import views

urlpatterns = [
    path('', views.ClinicListView.as_view(), name='clinic_list'),
    path('<int:pk>/', views.ClinicDetailView.as_view(), name='clinic_detail'),
    path('create/', views.ClinicCreateView.as_view(), name='clinic_create'),
    path('<int:pk>/update/', views.ClinicUpdateView.as_view(), name='clinic_update'),
]