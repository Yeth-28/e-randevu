from django.urls import path
from .api import ClinicListCreateAPIView, ClinicDetailAPIView

urlpatterns = [
    path('', ClinicListCreateAPIView.as_view(), name='api_clinic_list'),
    path('<int:pk>/', ClinicDetailAPIView.as_view(), name='api_clinic_detail'),
]