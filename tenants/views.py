from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.http import HttpResponseForbidden
from django.utils.text import slugify
from django.db.models import Count
from django.utils import timezone
from django.core.mail import send_mail
from datetime import timedelta
from functools import wraps

from .models import Clinic, Domain
from users.models import User
from patients.models import Patient, Visit, Appointment
from doctors.models import Doctor
import random, string, re


# ─── YARDIMCI ───────────────────────────────────────────────────

def generate_clinic_id():
    chars = string.ascii_uppercase + string.digits
    while True:
        new_id = ''.join(random.choices(chars, k=6))
        if not Clinic.objects.filter(clinic_id=new_id).exists():
            return new_id


def _hosts_dosyasina_ekle(subdomain):
    """Windows hosts dosyasına subdomain ekle — sadece geliştirme ortamı"""
    import os
    hosts_path = r'C:\Windows\System32\drivers\etc\hosts'
    entry = f"127.0.0.1 {subdomain}.localhost"

    try:
        with open(hosts_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if entry in content:
            return  # Zaten var

        with open(hosts_path, 'a', encoding='utf-8') as f:
            f.write(f"\n{entry}\n")
    except PermissionError:
        pass
    except Exception:
        pass


def generate_subdomain(name):
    tr_map = str.maketrans('çğıöşüÇĞİÖŞÜ', 'cgiosucgiosu')
    name = name.translate(tr_map)
    slug = slugify(name) or 'klinik'
    base_domain = getattr(settings, 'BASE_DOMAIN', 'localhost')
    subdomain = slug
    counter = 1
    while True:
        clinic_exists = Clinic.objects.filter(subdomain=subdomain).exists()
        domain_exists = Domain.objects.filter(domain=f"{subdomain}.{base_domain}").exists()
        if not clinic_exists and not domain_exists:
            break
        subdomain = f"{slug}-{counter}"
        counter += 1
    return subdomain


def validate_password(password):
    errors = []
    if len(password) < 8:
        errors.append('Şifre en az 8 karakter olmalı.')
    if not re.search(r'[A-Z]', password):
        errors.append('En az bir büyük harf içermeli.')
    if not re.search(r'[a-z]', password):
        errors.append('En az bir küçük harf içermeli.')
    if not re.search(r'\d', password):
        errors.append('En az bir rakam içermeli.')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-]', password):
        errors.append('En az bir özel karakter içermeli (!@#$%... gibi).')
    return errors


def send_clinic_welcome_email(clinic):
    try:
        send_mail(
            subject='e-Randevu — Klinik Kaydınız Tamamlandı',
            message=f"""Sayın {clinic.name},

Klinik kaydınız başarıyla oluşturuldu!

Klinik ID: {clinic.clinic_id}
Panel Adresi: {settings.PANEL_URL}/{clinic.clinic_id}/

Panele giriş için klinik ID, e-posta ve şifrenizi kullanın.

Saygılarımızla,
e-Randevu Ekibi""",
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@e-randevu.online'),
            recipient_list=[clinic.email],
            fail_silently=True,
        )
    except Exception:
        pass


# ─── KLİNİK KAYIT (ÇOK ADIMLI) ────────────────────────────────

PLAN_CHOICES = [
    ('free',       'Ücretsiz', '0 ₺/ay',    ['5 hasta', '1 doktor', 'Temel özellikler']),
    ('pro',        'Pro',      '499 ₺/ay',   ['Sınırsız hasta', '5 doktor', 'Online randevu', 'Raporlama']),
    ('enterprise', 'Kurumsal', '999 ₺/ay',   ['Sınırsız her şey', '2FA giriş', 'Öncelikli destek']),
]


def klinik_kayit(request):
    if request.method == 'POST':
        step = request.POST.get('step', '1')

        # ── ADIM 1: Bilgiler ──
        if step == '1':
            name      = request.POST.get('name', '').strip()
            email     = request.POST.get('email', '').strip().lower()
            phone     = request.POST.get('phone', '').strip()
            city      = request.POST.get('city', '').strip()
            address   = request.POST.get('address', '').strip()
            password1 = request.POST.get('password1', '')
            password2 = request.POST.get('password2', '')

            errors = []
            if not name:      errors.append('Klinik adı zorunlu.')
            if not email:     errors.append('E-posta zorunlu.')
            if not phone:     errors.append('Telefon zorunlu.')
            if not password1: errors.append('Şifre zorunlu.')
            if password1 != password2:
                errors.append('Şifreler eşleşmiyor.')
            errors.extend(validate_password(password1))
            if User.objects.filter(email=email).exists():
                errors.append('Bu e-posta zaten kayıtlı.')

            if errors:
                for e in errors:
                    messages.error(request, e)
                return render(request, 'panel/kayit.html', {
                    'step': 1, 'plan_choices': PLAN_CHOICES, 'form_data': request.POST,
                })

            request.session['kayit_data'] = {
                'name': name, 'email': email, 'phone': phone,
                'city': city, 'address': address, 'password': password1,
            }
            return render(request, 'panel/kayit.html', {
                'step': 2, 'plan_choices': PLAN_CHOICES,
            })

        # ── ADIM 2: Plan ──
        elif step == '2':
            plan = request.POST.get('plan', 'free')
            request.session['kayit_plan'] = plan

            if plan == 'free':
                return _klinik_kaydet(request)
            else:
                return render(request, 'panel/kayit.html', {
                    'step': 3, 'plan': plan, 'plan_choices': PLAN_CHOICES,
                    'kayit_data': request.session.get('kayit_data', {}),
                })

        # ── ADIM 3: Ödeme ──
        elif step == '3':
            return _iyzico_odeme(request)

    # GET — adım 1
    return render(request, 'panel/kayit.html', {
        'step': 1, 'plan_choices': PLAN_CHOICES,
    })


def _klinik_kaydet(request):
    data = request.session.get('kayit_data', {})
    plan = request.session.get('kayit_plan', 'free')

    if not data:
        messages.error(request, 'Oturum süresi doldu, tekrar deneyin.')
        return redirect(f"{settings.PANEL_URL}/kayit/")

    subdomain = generate_subdomain(data['name'])
    clinic_id = generate_clinic_id()
    base_domain = getattr(settings, 'BASE_DOMAIN', 'localhost')

    # Clinic zaten varsa al
    existing_clinic = Clinic.objects.filter(subdomain=subdomain).first()
    if existing_clinic:
        clinic = existing_clinic
        clinic_id = clinic.clinic_id
    else:
        clinic = Clinic(
            schema_name=subdomain,
            name=data['name'],
            email=data['email'],
            phone=data.get('phone', ''),
            city=data.get('city', ''),
            address=data.get('address', ''),
            plan=plan,
            clinic_id=clinic_id,
            subdomain=subdomain,
            is_active=True,
            is_visible=False,
            email_verified=False,
        )
        clinic.save()

    # Domain zaten varsa oluşturma (çift submit koruması)
    if not Domain.objects.filter(domain=f"{subdomain}.{base_domain}").exists():
        Domain.objects.create(
            domain=f"{subdomain}.{base_domain}",
            tenant=clinic,
            is_primary=True,
        )
        if base_domain == 'localhost':
            _hosts_dosyasina_ekle(subdomain)

    # Kullanıcı zaten varsa al, yoksa oluştur
    user, user_created = User.objects.get_or_create(
        email=data['email'],
        defaults={
            'username': data['email'],
            'role': 'clinic_owner',
        }
    )
    if user_created:
        user.set_password(data['password'])
        user.save()
    login(request, user)

    send_clinic_welcome_email(clinic)

    for key in ['kayit_data', 'kayit_plan']:
        request.session.pop(key, None)

    messages.success(request, f"✅ Klinik oluşturuldu! ID: {clinic_id} — E-postanıza gönderildi.")
    return redirect(f"{settings.PANEL_URL}/{clinic_id}/")


def _iyzico_odeme(request):
    from tenants.iyzico import odeme_baslat
    data = request.session.get('kayit_data', {})
    plan = request.session.get('kayit_plan', 'pro')

    card_number = request.POST.get('card_number', '').replace(' ', '')
    expiry      = request.POST.get('expiry', '')
    cvv         = request.POST.get('cvv', '').strip()
    card_holder = request.POST.get('card_holder', '').strip()

    exp_parts = expiry.split('/')
    exp_month = exp_parts[0].strip() if len(exp_parts) > 0 else '12'
    exp_year  = ('20' + exp_parts[1].strip()) if len(exp_parts) > 1 else '2030'

    class TempClinic:
        clinic_id = 'KAYIT'
    temp_clinic = TempClinic()

    name_parts = data.get('name', 'Klinik Sahibi').split(' ', 1)
    buyer_name    = name_parts[0]
    buyer_surname = name_parts[1] if len(name_parts) > 1 else 'Sahibi'

    sonuc = odeme_baslat(
        clinic=temp_clinic,
        plan_key=plan,
        period='monthly',
        buyer_info={
            'name':    buyer_name,
            'surname': buyer_surname,
            'email':   data.get('email', ''),
            'phone':   data.get('phone', '+905000000000'),
            'city':    data.get('city', 'İstanbul'),
            'address': data.get('address', 'Türkiye'),
            'ip':      request.META.get('REMOTE_ADDR', '85.34.78.112'),
        },
        card_info={
            'holder':    card_holder,
            'number':    card_number,
            'exp_month': exp_month,
            'exp_year':  exp_year,
            'cvc':       cvv,
        },
        callback_url=f"{settings.PANEL_URL}/kayit/",
    )

    if sonuc.get('success'):
        return _klinik_kaydet(request)
    else:
        messages.error(request, f"❌ Ödeme hatası: {sonuc.get('message', 'Bilinmeyen hata.')}")
        return render(request, 'panel/kayit.html', {
            'step': 3, 'plan': plan, 'plan_choices': PLAN_CHOICES,
            'kayit_data': data,
        })


# ─── PANEL GİRİŞ (SADELEŞTİRİLMİŞ — OTP SİZ) ──────────────────────

def panel_giris(request):
    if request.method == 'POST':
        clinic_id = request.POST.get('clinic_id', '').upper().strip()
        email     = request.POST.get('email', '').strip()
        password  = request.POST.get('password', '')

        # 1. Klinik varlığını kontrol et
        try:
            clinic = Clinic.objects.get(clinic_id=clinic_id)
        except Clinic.DoesNotExist:
            messages.error(request, '❌ Klinik ID bulunamadı.')
            return render(request, 'panel_giris.html', {'step': 'giris'})

        # 2. Kullanıcıyı doğrula
        user = authenticate(request, username=email, password=password)
        if user is None:
            messages.error(request, '❌ E-posta veya şifre hatalı.')
            return render(request, 'panel_giris.html', {'step': 'giris'})

        # 3. Oturum aç ve doğrudan kliniğin paneline yönlendir
        login(request, user)
        messages.success(request, f"Hoş geldiniz, {clinic.name} paneline yönlendiriliyorsunuz.")
        return redirect(f"{settings.PANEL_URL}/{clinic_id}/")

    return render(request, 'panel_giris.html', {'step': 'giris'})


# ─── PANEL DASHBOARD ────────────────────────────────────────────

def panel_dashboard(request, clinic_id):
    if not request.user.is_authenticated:
        return redirect(f"{settings.PANEL_URL}/giris/")

    try:
        clinic = Clinic.objects.get(clinic_id=clinic_id)
    except Clinic.DoesNotExist:
        messages.error(request, 'Klinik bulunamadı!')
        return redirect(f"{settings.PANEL_URL}/giris/")

    filtre = request.GET.get('filtre', 'ay')
    bugun  = timezone.now().date()

    if filtre == 'gun':
        baslangic    = bugun
        filtre_label = 'Bugün'
    elif filtre == 'hafta':
        baslangic    = bugun - timedelta(days=bugun.weekday())
        filtre_label = 'Bu Hafta'
    else:
        baslangic    = bugun.replace(day=1)
        filtre_label = 'Bu Ay'

    gecen_ay_bas = (bugun.replace(day=1) - timedelta(days=1)).replace(day=1)
    bu_ay_bas    = bugun.replace(day=1)

    aktif_hasta      = Patient.objects.filter(clinic=clinic, status='aktif').count()
    aktif_doktor     = Doctor.objects.filter(clinic=clinic, is_active=True).count()
    donem_ziyaret    = Visit.objects.filter(patient__clinic=clinic, date_time__date__gte=baslangic).count()
    gecen_ay_ziyaret = Visit.objects.filter(patient__clinic=clinic, date_time__date__gte=gecen_ay_bas, date_time__date__lt=bu_ay_bas).count()
    bugun_ziyaret    = Visit.objects.filter(patient__clinic=clinic, date_time__date=bugun).count()
    odenmemis        = Visit.objects.filter(patient__clinic=clinic, is_paid=False).count()
    bekleyen_randevu = Appointment.objects.filter(doctor__clinic=clinic, status='bekliyor', date_time__date__gte=bugun).count()

    from django.db.models.functions import TruncDate
    gunluk = (
        Visit.objects
        .filter(patient__clinic=clinic, date_time__date__gte=baslangic)
        .annotate(gun=TruncDate('date_time'))
        .values('gun')
        .annotate(sayi=Count('id'))
        .order_by('gun')
    )
    grafik_labels = [str(g['gun']) for g in gunluk]
    grafik_data   = [g['sayi'] for g in gunluk]

    son_ziyaretler = Visit.objects.filter(patient__clinic=clinic).select_related('patient', 'doctor').order_by('-date_time')[:8]
    son_hastalar   = Patient.objects.filter(clinic=clinic).order_by('-created_at')[:5]

    return render(request, 'panel/dashboard.html', {
        'clinic':            clinic,
        'clinic_id':         clinic_id,
        'aktif_hasta':       aktif_hasta,
        'aktif_doktor':      aktif_doktor,
        'donem_ziyaret':     donem_ziyaret,
        'gecen_ay_ziyaret':  gecen_ay_ziyaret,
        'bugun_ziyaret':     bugun_ziyaret,
        'odenmemis':         odenmemis,
        'bekleyen_randevu':  bekleyen_randevu,
        'grafik_labels':     grafik_labels,
        'grafik_data':       grafik_data,
        'son_ziyaretler':    son_ziyaretler,
        'son_hastalar':      son_hastalar,
        'filtre':            filtre,
        'filtre_label':      filtre_label,
    })


# ─── SUPERADMIN ─────────────────────────────────────────────────

def superadmin_giris_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/superadmin/giris/')
        if not request.user.is_staff:
            return HttpResponseForbidden('<h1>Yetkisiz Erişim</h1>')
        return view_func(request, *args, **kwargs)
    return wrapper


def superadmin_giris(request):
    error = None
    if request.method == 'POST':
        email    = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user     = authenticate(request, username=email, password=password)
        if user and user.is_staff:
            login(request, user)
            return redirect('/superadmin/')
        error = 'E-posta/şifre hatalı veya yetkiniz yok!'
    return render(request, 'superadmin/giris.html', {'error': error})


@superadmin_giris_required
def superadmin_dashboard(request):
    klinikler = Clinic.objects.exclude(schema_name='public').order_by('-created_at')
    stats = []
    for klinik in klinikler:
        stats.append({
            'klinik':         klinik,
            'hasta_sayisi':   Patient.objects.filter(clinic=klinik, status='aktif').count(),
            'doktor_sayisi':  Doctor.objects.filter(clinic=klinik, is_active=True).count(),
            'randevu_sayisi': Appointment.objects.filter(clinic=klinik).count(),
        })
    toplam = {
        'klinik': klinikler.count(),
        'hasta':  Patient.objects.count(),
        'doktor': Doctor.objects.count(),
    }
    return render(request, 'superadmin/dashboard.html', {'stats': stats, 'toplam': toplam})


@superadmin_giris_required
def superadmin_klinik_detay(request, clinic_id):
    klinik     = get_object_or_404(Clinic, clinic_id=clinic_id)
    hastalar   = Patient.objects.filter(clinic=klinik).order_by('-created_at')
    doktorlar  = Doctor.objects.filter(clinic=klinik).order_by('name')
    ziyaretler = Visit.objects.filter(patient__clinic=klinik).order_by('-date_time')[:50]
    return render(request, 'superadmin/klinik_detay.html', {
        'klinik': klinik, 'hastalar': hastalar,
        'doktorlar': doktorlar, 'ziyaretler': ziyaretler,
    })


@superadmin_giris_required
def superadmin_klinik_duzenle(request, clinic_id):
    klinik = get_object_or_404(Clinic, clinic_id=clinic_id)
    if request.method == 'POST':
        klinik.name           = request.POST.get('name', klinik.name)
        klinik.email          = request.POST.get('email', klinik.email)
        klinik.phone_number   = request.POST.get('phone', klinik.phone_number)
        klinik.city           = request.POST.get('city', klinik.city)
        klinik.plan           = request.POST.get('plan', klinik.plan)
        klinik.is_active      = request.POST.get('is_active') == 'on'
        klinik.is_visible     = request.POST.get('is_visible') == 'on'
        klinik.email_verified = request.POST.get('email_verified') == 'on'
        klinik.plan_end_date  = request.POST.get('plan_end_date') or None
        klinik.save()
        messages.success(request, f'{klinik.name} güncellendi!')
        return redirect(f'/superadmin/klinik/{clinic_id}/')
    return render(request, 'superadmin/klinik_duzenle.html', {
        'klinik': klinik, 'plan_choices': Clinic.PLAN_CHOICES,
    })