from rest_framework import generics
from .models import Doctor
from .serializers import DoctorSerializer

class DoctorListCreateAPIView(generics.ListCreateAPIView):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer

class DoctorDetailAPIView(generics.RetrieveAPIView):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer

class DoctorListAPIView(generics.ListAPIView):
    serializer_class = DoctorSerializer

    def get_queryset(self):
        clinic_id = self.request.query_params.get('clinic')
        procedure = self.request.query_params.get('procedure')
        if clinic_id and procedure:
            return Doctor.objects.filter(clinic_affiliations__clinic_id=clinic_id, specialties__contains=[procedure])
        return Doctor.objects.all()
