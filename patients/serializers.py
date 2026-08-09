from rest_framework import serializers
from .models import Patient, Visit

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['id', 'name', 'date_of_birth', 'phone_number', 'email', 'gender', 'blood_type', 'status']

class VisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visit
        fields = ['id', 'patient', 'doctor', 'date_time', 'procedures', 'notes', 'fee', 'is_paid']