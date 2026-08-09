from django.contrib import admin
from .models import Patient, Visit, PatientFile, ToothRecord

admin.site.register(Patient)
admin.site.register(Visit)
admin.site.register(PatientFile)
admin.site.register(ToothRecord)