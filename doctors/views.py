from django.conf import settings
import uuid

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from tenants.models import Clinic
from .models import Doctor


def get_clinic(clinic_id):
    return get_object_or_404(Clinic, clinic_id=clinic_id)


def generate_npi():
    while True:
        npi = str(uuid.uuid4())[:8].upper()
        if not Doctor.objects.filter(npi=npi).exists():
            return npi


@login_required
def doktor_listesi(request, clinic_id):
    clinic = get_clinic(clinic_id)
    doktorlar = Doctor.objects.filter(clinic=clinic, is_active=True).order_by('name')
    return render(request, 'panel/doktorlar/liste.html', {
        'doktorlar': doktorlar,
        'clinic_id': clinic_id,
    })


@login_required
def doktor_ekle(request, clinic_id):
    clinic = get_clinic(clinic_id)
    specialties = Doctor.SPECIALTIES

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        about = request.POST.get('about', '').strip()
        selected_specialties = request.POST.getlist('specialties')
        photo = request.FILES.get('photo')

        if not name:
            messages.error(request, 'Ad Soyad zorunludur!')
            return render(request, 'panel/doktorlar/ekle.html', {
                'specialties': specialties,
                'clinic_id': clinic_id,
            })

        if not selected_specialties:
            messages.error(request, 'En az bir uzmanlık alanı seçmelisiniz!')
            return render(request, 'panel/doktorlar/ekle.html', {
                'specialties': specialties,
                'clinic_id': clinic_id,
            })

        doktor = Doctor(
            clinic=clinic,
            npi=generate_npi(),
            name=name,
            email=email,
            phone_number=phone,
            specialties=selected_specialties,
            about=about if about else None,
        )

        if photo:
            doktor.photo = photo

        doktor.save()
        messages.success(request, f'{name} başarıyla eklendi!')
        return redirect(f"{settings.PANEL_URL}/{clinic_id}/doktorlar/")

    return render(request, 'panel/doktorlar/ekle.html', {
        'specialties': specialties,
        'clinic_id': clinic_id,
    })


@login_required
def doktor_duzenle(request, clinic_id, doktor_id):
    clinic = get_clinic(clinic_id)
    doktor = get_object_or_404(Doctor, id=doktor_id, clinic=clinic)
    specialties = Doctor.SPECIALTIES

    if request.method == 'POST':
        doktor.name = request.POST.get('name', '').strip()
        doktor.email = request.POST.get('email', '').strip()
        doktor.phone_number = request.POST.get('phone', '').strip()
        doktor.about = request.POST.get('about', '').strip() or None
        doktor.specialties = request.POST.getlist('specialties')

        photo = request.FILES.get('photo')
        if photo:
            doktor.photo = photo

        doktor.save()
        messages.success(request, f'{doktor.name} güncellendi!')
        return redirect(f"{settings.PANEL_URL}/{clinic_id}/doktorlar/")

    return render(request, 'panel/doktorlar/duzenle.html', {
        'doktor': doktor,
        'specialties': specialties,
        'clinic_id': clinic_id,
    })


@login_required
def doktor_sil(request, clinic_id, doktor_id):
    clinic = get_clinic(clinic_id)
    doktor = get_object_or_404(Doctor, id=doktor_id, clinic=clinic)

    if request.method == 'POST':
        doktor.is_active = False
        doktor.save()
        messages.success(request, f'{doktor.name} silindi!')
        return redirect(f"{settings.PANEL_URL}/{clinic_id}/doktorlar/")

    return render(request, 'panel/doktorlar/sil.html', {
        'doktor': doktor,
        'clinic_id': clinic_id,
    })