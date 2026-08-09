from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
# Clinic artık tenants uygulamasında!
from tenants.models import Clinic


class ClinicListView(LoginRequiredMixin, ListView):
    model = Clinic
    template_name = 'clinics/clinic_list.html'
    context_object_name = 'clinics'


class ClinicDetailView(LoginRequiredMixin, DetailView):
    model = Clinic
    template_name = 'clinics/clinic_detail.html'


class ClinicCreateView(LoginRequiredMixin, CreateView):
    model = Clinic
    template_name = 'clinics/clinic_form.html'
    fields = ['name', 'phone_number', 'email', 'address', 'city']
    success_url = reverse_lazy('clinic_list')


class ClinicUpdateView(LoginRequiredMixin, UpdateView):
    model = Clinic
    template_name = 'clinics/clinic_form.html'
    fields = ['name', 'phone_number', 'email', 'address', 'city']
    success_url = reverse_lazy('clinic_list')


def get_clinics_by_procedure(request):
    if request.method == 'POST':
        procedure = request.POST.get('procedure')
        clinics = Clinic.objects.filter(
            doctors__specialties__contains=[procedure]
        ).distinct()
        data = {
            'clinics': [{'id': clinic.id, 'name': clinic.name} for clinic in clinics]
        }
        return JsonResponse(data)


def clinic_detail(request, pk):
    clinic = get_object_or_404(Clinic, pk=pk)
    return render(request, 'clinics/clinic_detail.html', {'clinic': clinic})


def home(request):
    return render(request, 'home.html')