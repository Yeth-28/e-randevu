from django.urls import path
from .api import DoctorListCreateAPIView, DoctorDetailAPIView

urlpatterns = [
    path('', DoctorListCreateAPIView.as_view(), name='api_doctor_list'),
]