from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from tenants.models import Clinic
from tenants.models import Clinic, ClinicCard, ClinicWorkingHours, ClinicHoliday, DoctorWorkingHours
from doctors.models import Doctor


def get_clinic(clinic_id):
    return Clinic.objects.get(clinic_id=clinic_id)


@login_required
def ayarlar(request, clinic_id):
    clinic   = get_clinic(clinic_id)
    doktorlar = Doctor.objects.filter(clinic=clinic, is_active=True)

    # Çalışma saatlerini 7 gün için hazırla (yoksa default oluştur)
    working_hours = {}
    for day in range(7):
        wh, _ = ClinicWorkingHours.objects.get_or_create(
            clinic=clinic, day=day,
            defaults={'is_open': day < 6, 'open_time': '09:00', 'close_time': '18:00'}
        )
        working_hours[day] = wh

    holidays = ClinicHoliday.objects.filter(clinic=clinic).order_by('date')

    # Doktor çalışma saatleri
    doktor_saatleri = {}
    for doktor in doktorlar:
        saatler = {}
        for day in range(7):
            dw, _ = DoctorWorkingHours.objects.get_or_create(
                doctor=doktor, day=day,
                defaults={'is_working': day < 6, 'start_time': '09:00', 'end_time': '18:00'}
            )
            saatler[day] = dw
        doktor_saatleri[doktor.id] = saatler

    kartlar = ClinicCard.objects.filter(clinic=clinic)

    return render(request, 'panel/ayarlar.html', {
        'clinic':          clinic,
        'clinic_id':       clinic_id,
        'doktorlar':       doktorlar,
        'working_hours':   working_hours,
        'holidays':        holidays,
        'doktor_saatleri': doktor_saatleri,
        'days':            ClinicWorkingHours.DAYS,
        'kartlar':         kartlar,
    })


@login_required
def ayarlar_klinik_bilgileri(request, clinic_id):
    clinic = get_clinic(clinic_id)
    if request.method == 'POST':
        clinic.name    = request.POST.get('name', clinic.name).strip()
        clinic.address = request.POST.get('address', '').strip()
        clinic.phone   = request.POST.get('phone', '').strip()
        clinic.email   = request.POST.get('email', '').strip()
        clinic.website = request.POST.get('website', '').strip()
        clinic.about   = request.POST.get('about', '').strip()
        if request.FILES.get('logo'):
            clinic.logo = request.FILES['logo']
        clinic.save()
        messages.success(request, '✅ Klinik bilgileri güncellendi.')
    return redirect(f"{settings.PANEL_URL}/{clinic_id}/ayarlar/?tab=klinik")


@login_required
def ayarlar_calisma_saatleri(request, clinic_id):
    clinic = get_clinic(clinic_id)
    if request.method == 'POST':
        for day in range(7):
            wh, _ = ClinicWorkingHours.objects.get_or_create(clinic=clinic, day=day)
            wh.is_open    = request.POST.get(f'day_{day}_open') == 'on'
            wh.open_time  = request.POST.get(f'day_{day}_start', '09:00')
            wh.close_time = request.POST.get(f'day_{day}_end', '18:00')
            wh.save()
        messages.success(request, '✅ Çalışma saatleri güncellendi.')
    return redirect(f"{settings.PANEL_URL}/{clinic_id}/ayarlar/?tab=saatler")


@login_required
def ayarlar_tatil_ekle(request, clinic_id):
    clinic = get_clinic(clinic_id)
    if request.method == 'POST':
        date = request.POST.get('date', '').strip()
        desc = request.POST.get('description', '').strip()
        recurring = request.POST.get('is_recurring') == 'on'
        if date:
            ClinicHoliday.objects.get_or_create(
                clinic=clinic, date=date,
                defaults={'description': desc, 'is_recurring': recurring}
            )
            messages.success(request, f'✅ {date} tatil olarak eklendi.')
        else:
            messages.error(request, 'Tarih seçiniz.')
    return redirect(f"{settings.PANEL_URL}/{clinic_id}/ayarlar/?tab=tatil")


@login_required
def ayarlar_tatil_sil(request, clinic_id, tatil_id):
    clinic = get_clinic(clinic_id)
    ClinicHoliday.objects.filter(id=tatil_id, clinic=clinic).delete()
    messages.success(request, 'Tatil günü silindi.')
    return redirect(f"{settings.PANEL_URL}/{clinic_id}/ayarlar/?tab=tatil")


@login_required
def ayarlar_randevu(request, clinic_id):
    clinic = get_clinic(clinic_id)
    if request.method == 'POST':
        clinic.appointment_duration     = int(request.POST.get('appointment_duration', 30))
        clinic.appointment_advance_days = int(request.POST.get('appointment_advance_days', 60))
        clinic.appointment_interval     = int(request.POST.get('appointment_interval', 15))
        clinic.appointments_open        = request.POST.get('appointments_open') == 'on'
        clinic.save()
        messages.success(request, '✅ Randevu ayarları güncellendi.')
    return redirect(f"{settings.PANEL_URL}/{clinic_id}/ayarlar/?tab=randevu")


@login_required
def ayarlar_bildirim(request, clinic_id):
    clinic = get_clinic(clinic_id)
    if request.method == 'POST':
        clinic.sms_notifications    = request.POST.get('sms_notifications') == 'on'
        clinic.email_notifications  = request.POST.get('email_notifications') == 'on'
        clinic.reminder_hours_before = int(request.POST.get('reminder_hours_before', 24))
        clinic.save()
        messages.success(request, '✅ Bildirim ayarları güncellendi.')
    return redirect(f"{settings.PANEL_URL}/{clinic_id}/ayarlar/?tab=bildirim")


@login_required
def ayarlar_doktor_saatleri(request, clinic_id):
    clinic = get_clinic(clinic_id)
    if request.method == 'POST':
        doktor_id = request.POST.get('doktor_id')
        try:
            doktor = Doctor.objects.get(id=doktor_id, clinic=clinic)
        except Doctor.DoesNotExist:
            messages.error(request, 'Doktor bulunamadı.')
            return redirect(f"{settings.PANEL_URL}/{clinic_id}/ayarlar/?tab=doktor")

        for day in range(7):
            dw, _ = DoctorWorkingHours.objects.get_or_create(doctor=doktor, day=day)
            dw.is_working  = request.POST.get(f'd_{doktor_id}_{day}_working') == 'on'
            dw.start_time  = request.POST.get(f'd_{doktor_id}_{day}_start', '09:00')
            dw.end_time    = request.POST.get(f'd_{doktor_id}_{day}_end', '18:00')
            dw.save()
        messages.success(request, f'✅ {doktor.name} çalışma saatleri güncellendi.')
    return redirect(f"{settings.PANEL_URL}/{clinic_id}/ayarlar/?tab=doktor")


@login_required
def ayarlar_kart_guncelle(request, clinic_id):
    """Yeni kart ekle"""
    clinic = get_clinic(clinic_id)
    if request.method == 'POST':
        card_number = request.POST.get('card_number', '').replace(' ', '')
        expiry      = request.POST.get('expiry', '').strip()
        card_holder = request.POST.get('card_holder', '').strip()
        billing_address = request.POST.get('billing_address', '').strip()
        billing_city    = request.POST.get('billing_city', '').strip()
        billing_zip     = request.POST.get('billing_zip', '').strip()
        billing_country = request.POST.get('billing_country', 'TR').strip()
        make_active     = request.POST.get('make_active') == 'on'

        if len(card_number) < 15:
            messages.error(request, 'Geçersiz kart numarası.')
            return redirect(f"{settings.PANEL_URL}/{clinic_id}/ayarlar/?tab=kartlar")

        # Kart markasını tahmin et
        if card_number.startswith('4'):
            brand = 'Visa'
        elif card_number.startswith(('51','52','53','54','55','2')):
            brand = 'Mastercard'
        elif card_number.startswith(('34','37')):
            brand = 'Amex'
        else:
            brand = 'Kart'

        # İlk kart ise otomatik aktif yap
        is_first = not ClinicCard.objects.filter(clinic=clinic).exists()

        kart = ClinicCard.objects.create(
            clinic=clinic,
            last4=card_number[-4:],
            brand=brand,
            holder=card_holder,
            expiry=expiry,
            billing_address=billing_address,
            billing_city=billing_city,
            billing_zip=billing_zip,
            billing_country=billing_country,
            is_active=(make_active or is_first),
        )
        messages.success(request, f'✅ {brand} •••• {kart.last4} kartı eklendi.')

    return redirect(f"{settings.PANEL_URL}/{clinic_id}/ayarlar/?tab=kartlar")


@login_required
def ayarlar_kart_aktif(request, clinic_id, kart_id):
    """Kartı aktif yap"""
    clinic = get_clinic(clinic_id)
    if request.method == 'POST':
        kart = get_object_or_404(ClinicCard, id=kart_id, clinic=clinic)
        ClinicCard.objects.filter(clinic=clinic, is_active=True).update(is_active=False)
        kart.is_active = True
        kart.save()
        messages.success(request, f'✅ {kart.brand} •••• {kart.last4} aktif kart olarak seçildi.')
    return redirect(f"{settings.PANEL_URL}/{clinic_id}/ayarlar/?tab=kartlar")


@login_required
def ayarlar_kart_sil(request, clinic_id, kart_id):
    """Kartı sil"""
    clinic = get_clinic(clinic_id)
    if request.method == 'POST':
        kart = get_object_or_404(ClinicCard, id=kart_id, clinic=clinic)
        brand, last4 = kart.brand, kart.last4
        was_active = kart.is_active
        kart.delete()
        # Silinen kart aktifse bir sonrakini aktif yap
        if was_active:
            sonraki = ClinicCard.objects.filter(clinic=clinic).first()
            if sonraki:
                sonraki.is_active = True
                sonraki.save()
        messages.success(request, f'🗑 {brand} •••• {last4} kartı silindi.')
    return redirect(f"{settings.PANEL_URL}/{clinic_id}/ayarlar/?tab=kartlar")


@login_required
def ayarlar_kart_duzenle(request, clinic_id, kart_id):
    """Mevcut kartı güncelle"""
    clinic = get_clinic(clinic_id)
    kart = get_object_or_404(ClinicCard, id=kart_id, clinic=clinic)
    if request.method == 'POST':
        card_number = request.POST.get('card_number', '').replace(' ', '')
        expiry      = request.POST.get('expiry', '').strip()
        card_holder = request.POST.get('card_holder', '').strip()
        billing_address = request.POST.get('billing_address', '').strip()
        billing_city    = request.POST.get('billing_city', '').strip()
        billing_zip     = request.POST.get('billing_zip', '').strip()
        billing_country = request.POST.get('billing_country', 'TR').strip()

        if card_number and len(card_number) >= 15:
            kart.last4 = card_number[-4:]
            if card_number.startswith('4'):
                kart.brand = 'Visa'
            elif card_number.startswith(('51','52','53','54','55','2')):
                kart.brand = 'Mastercard'
            elif card_number.startswith(('34','37')):
                kart.brand = 'Amex'
            else:
                kart.brand = 'Kart'

        if expiry:      kart.expiry = expiry
        if card_holder: kart.holder = card_holder
        kart.billing_address = billing_address
        kart.billing_city    = billing_city
        kart.billing_zip     = billing_zip
        kart.billing_country = billing_country
        kart.save()
        messages.success(request, f'✅ {kart.brand} •••• {kart.last4} kartı güncellendi.')

    return redirect(f"{settings.PANEL_URL}/{clinic_id}/ayarlar/?tab=kartlar")


@login_required
def ayarlar_kart_aktif_sec(request, clinic_id):
    """Radio button ile aktif kart seç"""
    clinic = get_clinic(clinic_id)
    if request.method == 'POST':
        kart_id = request.POST.get('aktif_kart_id')
        if kart_id:
            kart = get_object_or_404(ClinicCard, id=kart_id, clinic=clinic)
            ClinicCard.objects.filter(clinic=clinic, is_active=True).update(is_active=False)
            kart.is_active = True
            kart.save()
            messages.success(request, f'✅ {kart.brand} •••• {kart.last4} aktif kart olarak seçildi.')
    return redirect(f"{settings.PANEL_URL}/{clinic_id}/ayarlar/?tab=kartlar")