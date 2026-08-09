from rest_framework import generics
from .models import Patient, Visit
from .serializers import PatientSerializer, VisitSerializer

class PatientListCreateAPIView(generics.ListCreateAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer

class VisitListCreateAPIView(generics.ListCreateAPIView):
    queryset = Visit.objects.all()
    serializer_class = VisitSerializer