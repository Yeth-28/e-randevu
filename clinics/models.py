# Clinic modeli artık tenants/models.py'de!
# Bu dosya boş kalabilir veya sadece DoctorAffiliation kalır.

from django.db import models

class DoctorAffiliation(models.Model):
    doctor = models.ForeignKey('doctors.Doctor', on_delete=models.CASCADE)
    office_address = models.TextField(blank=True)
    working_schedule = models.TextField(blank=True)

    def __str__(self):
        return f"{self.doctor} - Bağlantı"