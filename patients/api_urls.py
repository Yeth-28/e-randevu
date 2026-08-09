from django.urls import path
from .api import PatientListCreateAPIView

urlpatterns = [
    path('', PatientListCreateAPIView.as_view(), name='api_patient_list'),
]