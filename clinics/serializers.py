from rest_framework import serializers
from tenants.models import Clinic
from .models import DoctorAffiliation

class ClinicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinic
        fields = ['id', 'name', 'phone_number', 'email', 'address', 'city', 'plan', 'is_active']

class DoctorAffiliationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorAffiliation
        fields = '__all__'