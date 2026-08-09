from django.contrib import admin
from tenants.models import Clinic, Domain
from .models import DoctorAffiliation

admin.site.register(Clinic)
admin.site.register(Domain)
admin.site.register(DoctorAffiliation)