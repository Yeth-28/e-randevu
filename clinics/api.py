from rest_framework import generics
from tenants.models import Clinic
from .serializers import ClinicSerializer


class ClinicListCreateAPIView(generics.ListCreateAPIView):
    queryset = Clinic.objects.all()
    serializer_class = ClinicSerializer


class ClinicDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Clinic.objects.all()
    serializer_class = ClinicSerializer