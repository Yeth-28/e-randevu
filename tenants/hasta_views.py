from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Count, Avg
from functools import wraps

from tenants.models import Clinic
from patients.models import (
    Patient, Visit, Appointment,
    HastaUser, HastaSession,
)
from doctors.models import Doctor


# ═══════════════════════════════════════════════════════
# YARDIMCI
# ═══════════════════════════════════════════════════════

def get_hasta_from_request(request):
    token = request.COOKIES.get('hasta_token')
    if not token:
        return None
    try:
        session = HastaSession.objects.select_related('hasta_user').get(token=token)
        if session.is_valid():
            return session.hasta_user
        session.delete()
    except HastaSession.DoesNotExist:
        pass
    return None


def hasta_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        hasta_user = get_hasta_from_request(request)
        if not hasta_user:
            return redirect(f"{settings.SITE_URL}/hasta/giris/")
        request.hasta_user = hasta_user
        return view_func(request, *args, **kwargs)
    return wrapper


# ═══════════════════════════════════════════════════════
# ANA SAYFA — klinik arama
# ═══════════════════════════════════════════════════════

def ana_sayfa(request):
    """e-randevu.online ana sayfası"""
    arama = request.GET.get('q', '').strip()
    sehir = request.GET.get('sehir', '').strip()
    klinikler = []
    toplam = 0

    if arama or sehir:
        qs = Clinic.objects.filter(is_active=True)
        if arama:
            qs = qs.filter(
                Q(name__icontains=arama) |
                Q(city__icontains=arama) |
                Q(address__icontains=arama)
            )
        if sehir:
            qs = qs.filter(city__icontains=sehir)
        klinikler = qs.order_by('name')[:20]
        toplam    = qs.count()

    # Öne çıkan klinikler (en çok randevusu olan)
    one_cikan = Clinic.objects.filter(
        is_active=True, plan__in=['pro', 'enterprise']
    ).order_by('?')[:6]

    # Şehir listesi
    sehirler = Clinic.objects.filter(
        is_active=True
    ).exclude(city='').values_list('city', flat=True).distinct().order_by('city')

    return render(request, 'hasta/ana_sayfa.html', {
        'arama':     arama,
        'sehir':     sehir,
        'klinikler': klinikler,
        'toplam':    toplam,
        'one_cikan': one_cikan,
        'sehirler':  list(sehirler),
        'hasta_user': get_hasta_from_request(request),
    })


def klinik_ara_api(request):
    """AJAX arama API"""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})
    base_domain = getattr(settings, 'BASE_DOMAIN', 'localhost')
    klinikler = Clinic.objects.filter(
        is_active=True
    ).filter(
        Q(name__icontains=q) | Q(city__icontains=q)
    ).values('name', 'city', 'address', 'subdomain')[:8]

    results = [
        {
            'name':     k['name'],
            'city':     k['city'],
            'address':  k['address'][:60] + '...' if k['address'] and len(k['address']) > 60 else k['address'],
            'url':      f"http://{k['subdomain']}.{base_domain}/",
        }
        for k in klinikler
    ]
    return JsonResponse({'results': results})


# ═══════════════════════════════════════════════════════
# KLİNİK SUBDOMAIN SAYFASI
# ═══════════════════════════════════════════════════════

def klinik_randevu_sayfasi(request):
    """aliklinik.e-randevu.online — kliniğe özel randevu sayfası"""
    host         = request.get_host().split(':')[0].lower()
    base_domain  = getattr(settings, 'BASE_DOMAIN',  'e-randevu.online')
    hasta_domain = getattr(settings, 'HASTA_DOMAIN', 'hasta.localhost')

    # Subdomain'i çıkar — aliklinik.e-randevu.online → aliklinik
    subdomain = host
    for suffix in [f'.{base_domain}', f'.{hasta_domain}', '.localhost', '.e-randevu.online']:
        if subdomain.endswith(suffix):
            subdomain = subdomain[:-len(suffix)]
            break

    try:
        clinic = Clinic.objects.get(subdomain=subdomain, is_active=True)
    except Clinic.DoesNotExist:
        return render(request, 'hasta/klinik_bulunamadi.html', {}, status=404)

    # Doktorları clinic'e göre filtrele (public schema'da kayıtlı)
    from django_tenants.utils import schema_context
    with schema_context('public'):
        doktorlar = list(Doctor.objects.filter(clinic=clinic, is_active=True))
    hasta_user = get_hasta_from_request(request)

    if request.method == 'POST':
        # Randevu form submit
        doktor_id   = request.POST.get('doktor_id')
        tarih_saat  = request.POST.get('tarih_saat')
        procedure   = request.POST.get('procedure', 'muayene')
        hasta_adi   = request.POST.get('hasta_adi', '').strip()
        hasta_tel   = request.POST.get('hasta_tel', '').strip().replace(' ', '')
        hasta_email = request.POST.get('hasta_email', '').strip()
        notlar      = request.POST.get('notlar', '').strip()

        if not doktor_id or not tarih_saat or not hasta_adi or not hasta_tel:
            messages.error(request, 'Lütfen tüm zorunlu alanları doldurun.')
            return redirect(request.path)

        try:
            from django_tenants.utils import schema_context
            with schema_context('public'):
                doktor = Doctor.objects.get(id=doktor_id, clinic=clinic, is_active=True)
        except Doctor.DoesNotExist:
            messages.error(request, 'Seçilen doktor bulunamadı.')
            return redirect(request.path)

        # Randevu ve hasta kaydını tenant schema'sında oluştur
        import datetime
        from django_tenants.utils import schema_context
        try:
            dt = datetime.datetime.fromisoformat(tarih_saat)
            import zoneinfo
            aware_dt = dt.replace(tzinfo=zoneinfo.ZoneInfo('Europe/Istanbul'))
        except Exception:
            messages.error(request, 'Geçersiz tarih formatı.')
            return redirect(request.path)

        with schema_context('public'):
            # Hasta kaydını bul veya oluştur — clinic bilgisiyle
            hasta, created = Patient.objects.get_or_create(
                phone_number=hasta_tel,
                clinic=clinic,
                defaults={
                    'name':   hasta_adi,
                    'email':  hasta_email,
                    'status': 'aktif',
                }
            )
            # Eğer kayıt varsa ama clinic atanmamışsa güncelle
            if not created and hasta.clinic is None:
                hasta.clinic = clinic
                hasta.save(update_fields=['clinic'])

            Appointment.objects.create(
                patient=hasta,
                doctor=doktor,
                date_time=aware_dt,
                procedure=procedure,
                status='onaylandi',
                notes=notlar,
                duration=clinic.appointment_duration,
            )

            from patients.models import Notification
            Notification.objects.create(
                clinic=clinic,
                type='yeni_randevu',
                title='Yeni Online Randevu',
                body=f'{hasta_adi} ({hasta_tel}) — {doktor.name} — {aware_dt.strftime("%d.%m.%Y %H:%M")}',
            )

        request.session['randevu_basarili'] = {
            'hasta_adi': hasta_adi,
            'doktor':    doktor.name,
            'tarih':     aware_dt.strftime('%d.%m.%Y %H:%M'),
        }
        return redirect(f'{request.path}basarili/')

    # Çalışma saatlerini getir — template'de hazır liste olarak gönder
    gun_listesi = []
    try:
        from tenants.models import ClinicWorkingHours
        wh_qs = ClinicWorkingHours.objects.filter(clinic=clinic)
        wh_dict = {wh.day: wh for wh in wh_qs}
        gun_adlari = {
            0: 'Pazartesi', 1: 'Salı', 2: 'Çarşamba', 3: 'Perşembe',
            4: 'Cuma', 5: 'Cumartesi', 6: 'Pazar'
        }
        for num, name in gun_adlari.items():
            wh = wh_dict.get(num)
            gun_listesi.append({
                'name':  name,
                'open':  wh.is_open if wh else False,
                'open_time':  wh.open_time.strftime('%H:%M') if wh and wh.is_open and wh.open_time else '',
                'close_time': wh.close_time.strftime('%H:%M') if wh and wh.is_open and wh.close_time else '',
            })
    except Exception:
        pass

    import datetime as dt_module
    import json as json_module
    from django.utils import timezone as tz_module
    local_tz = tz_module.get_current_timezone()
    bugun = dt_module.date.today()

    # Randevu ayarları
    randevu_suresi    = getattr(clinic, 'appointment_duration', 30)     # dk
    randevu_aralik    = getattr(clinic, 'appointment_interval', 15)      # dk
    max_ileri_gun     = getattr(clinic, 'appointment_advance_days', 60)  # gün

    # Tatil günleri
    tatil_listesi = []
    tatil_tarihleri = set()
    try:
        from tenants.models import ClinicHoliday
        tatiller = ClinicHoliday.objects.filter(clinic=clinic, date__gte=bugun).order_by('date')
        for t in tatiller:
            tatil_listesi.append({
                'date': t.date.strftime('%Y-%m-%d'),
                'date_display': t.date.strftime('%d %B %Y'),
                'name': t.name,
            })
            tatil_tarihleri.add(t.date.strftime('%Y-%m-%d'))
    except Exception:
        pass

    # Çalışma saatlerine göre kapalı günler
    kapali_gunler = set()  # haftanın gün numaraları (0=Pzt, 6=Paz)
    gun_saatleri = {}      # {0: ('09:00','18:00'), ...}
    with schema_context('public'):
        wh_qs = ClinicWorkingHours.objects.filter(clinic=clinic)
        for wh in wh_qs:
            if not wh.is_open:
                kapali_gunler.add(wh.day)
            else:
                if wh.open_time and wh.close_time:
                    gun_saatleri[wh.day] = (
                        wh.open_time.strftime('%H:%M'),
                        wh.close_time.strftime('%H:%M')
                    )

    # Mevcut randevuları çek — dolu slotları hesapla
    bitis_tarihi = bugun + dt_module.timedelta(days=max_ileri_gun)
    # dolu_araliklar: {'2026-03-20': [(540, 570), (600, 660)]} — dakika cinsinden
    dolu_araliklar = {}
    with schema_context('public'):
        randevular = list(Appointment.objects.filter(
            doctor__clinic=clinic,
            date_time__date__gte=bugun,
            date_time__date__lte=bitis_tarihi,
            status__in=['bekliyor', 'onaylandi'],
        ).values_list('date_time', 'duration'))

    for rdt, rdur in randevular:
        local_dt = rdt.astimezone(local_tz)
        gun_str  = local_dt.strftime('%Y-%m-%d')
        bas_dk   = local_dt.hour * 60 + local_dt.minute
        bit_dk   = bas_dk + (rdur or randevu_suresi)
        if gun_str not in dolu_araliklar:
            dolu_araliklar[gun_str] = []
        dolu_araliklar[gun_str].append([bas_dk, bit_dk])

    # Her gün için musait slot listesi üret
    musait_slotlar = {}   # {'2026-03-20': ['09:00','09:30',...]}
    tum_slotlar    = {}   # tüm slotlar (dolu+müsait)
    dolu_gunler    = []   # tüm gün dolu ya da kapalı

    gun = bugun
    while gun <= bitis_tarihi:
        gun_str    = gun.strftime('%Y-%m-%d')
        hafta_gunu = gun.weekday()  # 0=Pzt

        # Tatil veya kapalı gün
        if gun_str in tatil_tarihleri or hafta_gunu in kapali_gunler:
            dolu_gunler.append(gun_str)
            gun += dt_module.timedelta(days=1)
            continue

        # Çalışma saatleri
        if hafta_gunu in gun_saatleri:
            ac_str, kap_str = gun_saatleri[hafta_gunu]
            ac_h, ac_m  = map(int, ac_str.split(':'))
            kap_h, kap_m = map(int, kap_str.split(':'))
            ac_dk  = ac_h * 60 + ac_m
            kap_dk = kap_h * 60 + kap_m
        else:
            # Varsayılan 09:00-18:00
            ac_dk, kap_dk = 540, 1080

        araliklar = dolu_araliklar.get(gun_str, [])
        tum_slotlar_gun = []
        musait_slotlar_gun = []
        slot_dk = ac_dk
        while slot_dk + randevu_suresi <= kap_dk:
            saat_str = f"{slot_dk // 60:02d}:{slot_dk % 60:02d}"
            tum_slotlar_gun.append(saat_str)
            slot_bitis = slot_dk + randevu_suresi
            cakisik = any(slot_dk < r_bit and slot_bitis > r_bas for r_bas, r_bit in araliklar)
            if not cakisik:
                musait_slotlar_gun.append(saat_str)
            slot_dk += randevu_aralik

        if not musait_slotlar_gun:
            dolu_gunler.append(gun_str)
        else:
            musait_slotlar[gun_str] = musait_slotlar_gun
        # Tüm slotları her zaman kaydet (dolu olanlar için gösterim)
        if tum_slotlar_gun:
            tum_slotlar[gun_str] = tum_slotlar_gun

        gun += dt_module.timedelta(days=1)

    # Doktor çalışma saatleri
    doktor_saatleri = {}
    try:
        from tenants.models import DoctorWorkingHours
        gun_adlari = {1:'Pzt',2:'Sal',3:'Çar',4:'Per',5:'Cum',6:'Cmt',7:'Paz'}
        for d in doktorlar:
            saatler = DoctorWorkingHours.objects.filter(doctor=d)
            doktor_saatleri[d.id] = [
                {
                    'gun': gun_adlari.get(s.day, ''),
                    'open': s.is_working,
                    'open_time': s.open_time.strftime('%H:%M') if s.is_open and s.open_time else '',
                    'close_time': s.close_time.strftime('%H:%M') if s.is_open and s.close_time else '',
                }
                for s in saatler.order_by('day')
            ]
    except Exception:
        pass

    # Doktorların uzmanlık alanlarından hizmet listesi oluştur
# hasta_views.py içinde şu bloğu bul ve değiştir:
# "# Doktorların uzmanlık alanlarından hizmet listesi oluştur" yorumundan başlayan kısım

# ── Hizmet listesi: aynı uzmanlık birden fazla doktorda varsa birleştir ──
    UZMANLIK_MAP = {
        'genel_dis':      ('🔍', 'Genel Muayene'),
        'implant':        ('🔩', 'İmplant'),
        'ortodonti':      ('😁', 'Ortodonti'),
        'cocuk_dis':      ('👶', 'Çocuk Diş Hekimliği'),
        'periodontoloji': ('🦷', 'Periodontoloji'),
        'endodonti':      ('💉', 'Kanal Tedavisi'),
        'protez':         ('🦷', 'Protez'),
        'estetik_dis':    ('✨', 'Estetik Diş Hekimliği'),
        'agiz_cerrahisi': ('🔧', 'Ağız Cerrahisi'),
        'radyoloji':      ('🩻', 'Radyoloji'),
        'dis_beyazlatma': ('⭐', 'Diş Beyazlatma'),
        'diger':          ('📋', 'Diğer'),
    }

    # spec -> {icon, name, doktor_id_listesi, doktor_adi_listesi}
    hizmet_dict = {}
    for d in doktorlar:
        if d.specialties:
            for spec in d.specialties:
                if spec not in UZMANLIK_MAP:
                    continue
                if spec not in hizmet_dict:
                    icon, name = UZMANLIK_MAP[spec]
                    hizmet_dict[spec] = {
                        'icon': icon,
                        'name': name,
                        'doktor_ids': [],      # filtre için
                        'doktor_adlari': [],   # gösterim için
                    }
                if str(d.id) not in hizmet_dict[spec]['doktor_ids']:
                    hizmet_dict[spec]['doktor_ids'].append(str(d.id))
                    hizmet_dict[spec]['doktor_adlari'].append(d.name)

    # Template için doktor_ids'i space-separated string yap (JS filtresi için)
    hizmetler = []
    for spec, h in hizmet_dict.items():
        hizmetler.append({
            'icon': h['icon'],
            'name': h['name'],
            'doktor_ids': ' '.join(h['doktor_ids']),   # "1 2 3" formatında
            'doktor_adlari': h['doktor_adlari'],
        })

    # Klinik çalışma saatleri
    from tenants.models import ClinicWorkingHours, ClinicHoliday, DoctorWorkingHours
    GUNLER = ['Pazartesi','Salı','Çarşamba','Perşembe','Cuma','Cumartesi','Pazar']
    klinik_saatleri = []
    tatil_detay = []
    with schema_context('public'):
        for day in range(7):
            try:
                wh = ClinicWorkingHours.objects.get(clinic=clinic, day=day)
                klinik_saatleri.append({
                    'gun': GUNLER[day],
                    'gun_num': day,
                    'is_open': wh.is_open,
                    'open_time': wh.open_time.strftime('%H:%M') if wh.open_time else '09:00',
                    'close_time': wh.close_time.strftime('%H:%M') if wh.close_time else '18:00',
                })
            except ClinicWorkingHours.DoesNotExist:
                klinik_saatleri.append({'gun': GUNLER[day], 'gun_num': day, 'is_open': day < 6, 'open_time': '09:00', 'close_time': '18:00'})

        for h in ClinicHoliday.objects.filter(clinic=clinic).order_by('date'):
            tatil_detay.append({
                'tarih': h.date.strftime('%d.%m.%Y'),
                'tarih_iso': h.date.isoformat(),
                'aciklama': h.description or '',
                'tekrar': h.is_recurring,
            })

    # Doktor çalışma günleri (hangi günler çalışıyor)
    doktor_calisma_gunleri = {}
    with schema_context('public'):
        for doktor in doktorlar:
            gunler = []
            try:
                dw_list = DoctorWorkingHours.objects.filter(doctor=doktor)
                for dw in dw_list:
                    if dw.is_working:
                        gunler.append({
                            'gun': GUNLER[dw.day],
                            'gun_num': dw.day,
                            'start': dw.start_time.strftime('%H:%M') if dw.start_time else '09:00',
                            'end': dw.end_time.strftime('%H:%M') if dw.end_time else '18:00',
                        })
            except Exception:
                pass
            doktor_calisma_gunleri[doktor.id] = gunler

    return render(request, 'hasta/klinik_randevu.html', {
        'clinic':                 clinic,
        'doktorlar':              doktorlar,
        'hasta_user':             hasta_user,
        'gun_listesi':            gun_listesi,
        'hizmetler':              hizmetler,
        'tatil_listesi':          tatil_listesi,
        'musait_slotlar':         json_module.dumps(musait_slotlar),
        'tum_slotlar':            json_module.dumps(tum_slotlar),
        'dolu_gunler':            json_module.dumps(dolu_gunler),
        'doktor_saatleri':        json_module.dumps({str(k): v for k, v in doktor_saatleri.items()}),
        'randevu_suresi':         randevu_suresi,
        'max_ileri_gun':          max_ileri_gun,
        'bugun_str':              bugun.strftime('%Y-%m-%d'),
        'max_tarih_str':          bitis_tarihi.strftime('%Y-%m-%d'),
        'klinik_saatleri':        klinik_saatleri,
        'klinik_saatleri_json':   json_module.dumps(klinik_saatleri, ensure_ascii=False),
        'tatil_detay':            tatil_detay,
        'doktor_calisma_gunleri': json_module.dumps({str(k): v for k, v in doktor_calisma_gunleri.items()}),
    })


def randevu_basarili(request):
    """Randevu alındı sayfası"""
    host      = request.get_host().split(':')[0].lower()
    subdomain = host.replace('.e-randevu.online', '').replace('.localhost', '')
    try:
        clinic = Clinic.objects.get(subdomain=subdomain, is_active=True)
    except Clinic.DoesNotExist:
        return redirect(f"{settings.SITE_URL}/")

    bilgi = request.session.pop('randevu_basarili', {})
    return render(request, 'hasta/randevu_basarili.html', {
        'clinic': clinic,
        'bilgi':  bilgi,
    })


# ═══════════════════════════════════════════════════════
# HASTA GİRİŞİ
# ═══════════════════════════════════════════════════════

def hasta_kayit(request):
    """Yeni hasta kaydı"""
    if get_hasta_from_request(request) and request.method == 'GET':
        return redirect(f"{settings.SITE_URL}/hasta/profilim/")

    if request.method == 'POST':
        first_name   = request.POST.get('first_name', '').strip()
        last_name    = request.POST.get('last_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        email        = request.POST.get('email', '').strip().lower()
        password     = request.POST.get('password', '')
        password2    = request.POST.get('password2', '')

        errors = []
        if not all([first_name, last_name, phone_number, email, password]):
            errors.append('Tüm alanları doldurunuz.')
        if password != password2:
            errors.append('Şifreler eşleşmiyor.')
        if len(password) < 6:
            errors.append('Şifre en az 6 karakter olmalı.')
        if HastaUser.objects.filter(email=email).exists():
            errors.append('Bu e-posta zaten kayıtlı.')
        if HastaUser.objects.filter(phone_number=phone_number).exists():
            errors.append('Bu telefon numarası zaten kayıtlı.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'hasta/kayit.html', {
                'form_data': request.POST
            })

        hasta_user = HastaUser(
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            email=email,
        )
        hasta_user.set_password(password)
        hasta_user.save()

        session = HastaSession.create_for(hasta_user)
        response = redirect(f"{settings.SITE_URL}/hasta/profilim/")
        response.set_cookie('hasta_token', session.token, max_age=30*24*3600, httponly=True, samesite='Lax')
        messages.success(request, 'Kayıt başarılı! Hoş geldiniz.')
        return response

    return render(request, 'hasta/kayit.html', {})


def hasta_giris(request):
    """Hasta girişi — e-posta + şifre"""
    # Zaten giriş yapmışsa sadece POST değilse yönlendir
    if get_hasta_from_request(request) and request.method == 'GET':
        return redirect(f"{settings.SITE_URL}/hasta/profilim/")

    if request.method == 'POST':
        email    = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        try:
            hasta_user = HastaUser.objects.get(email=email, is_active=True)
        except HastaUser.DoesNotExist:
            messages.error(request, 'E-posta veya şifre hatalı.')
            return render(request, 'hasta/giris.html', {})

        if not hasta_user.check_password(password):
            messages.error(request, 'E-posta veya şifre hatalı.')
            return render(request, 'hasta/giris.html', {})

        hasta_user.last_login = timezone.now()
        hasta_user.save(update_fields=['last_login'])

        session = HastaSession.create_for(hasta_user)
        response = redirect(f"{settings.SITE_URL}/hasta/profilim/")
        response.set_cookie('hasta_token', session.token, max_age=30*24*3600, httponly=True, samesite='Lax')
        return response

    return render(request, 'hasta/giris.html', {})


def hasta_cikis(request):
    token = request.COOKIES.get('hasta_token')
    if token:
        HastaSession.objects.filter(token=token).delete()
    response = redirect(f"{settings.SITE_URL}/")
    response.delete_cookie('hasta_token')
    return response


# ═══════════════════════════════════════════════════════
# HASTA PROFİLİ — e-Nabız
# ═══════════════════════════════════════════════════════

@hasta_login_required
def hasta_profili(request):
    hasta_user = request.hasta_user

    # Profil güncelleme
    if request.method == 'POST':
        action = request.POST.get('action', 'profil')
        if action == 'profil':
            first_name   = request.POST.get('first_name', '').strip()
            last_name    = request.POST.get('last_name', '').strip()
            phone_number = request.POST.get('phone_number', '').strip().replace(' ', '')
            email        = request.POST.get('email', '').strip().lower()
            blood_type   = request.POST.get('blood_type', '').strip()
            ins_company  = request.POST.get('insurance_company', '').strip()
            ins_number   = request.POST.get('insurance_number', '').strip()

            if email != hasta_user.email:
                from patients.models import HastaUser as HU
                if HU.objects.filter(email=email).exclude(id=hasta_user.id).exists():
                    messages.error(request, 'Bu e-posta başka bir hesapta kayıtlı.')
                    return redirect(f"{settings.SITE_URL}/hasta/profilim/")

            hasta_user.first_name        = first_name
            hasta_user.last_name         = last_name
            hasta_user.phone_number      = phone_number
            hasta_user.email             = email
            hasta_user.blood_type        = blood_type
            hasta_user.insurance_company = ins_company
            hasta_user.insurance_number  = ins_number
            hasta_user.save()
            messages.success(request, 'Profil güncellendi.')

        elif action == 'sifre':
            eski    = request.POST.get('eski_sifre', '')
            yeni    = request.POST.get('yeni_sifre', '')
            yeni2   = request.POST.get('yeni_sifre2', '')
            if not hasta_user.check_password(eski):
                messages.error(request, 'Mevcut şifre hatalı.')
            elif yeni != yeni2:
                messages.error(request, 'Yeni şifreler eşleşmiyor.')
            elif len(yeni) < 6:
                messages.error(request, 'Şifre en az 6 karakter olmalı.')
            else:
                hasta_user.set_password(yeni)
                hasta_user.save()
                messages.success(request, 'Şifre güncellendi.')

        return redirect(f"{settings.SITE_URL}/hasta/profilim/")

    # Telefon ile public schema'da hasta kayıtlarını bul
    from django_tenants.utils import schema_context
    with schema_context('public'):
        randevular_qs = Appointment.objects.filter(
            patient__phone_number=hasta_user.phone_number
        ).select_related('doctor', 'patient', 'patient__clinic').order_by('-date_time')

        ziyaretler_qs = Visit.objects.filter(
            patient__phone_number=hasta_user.phone_number
        ).select_related('doctor', 'patient', 'patient__clinic').order_by('-date_time')

        # Visit işlemlerini prefetch et
        from patients.models import ToothRecord
        randevular   = list(randevular_qs[:30])
        ziyaretler   = list(ziyaretler_qs[:30])

        # Her ziyaret için tooth record ve ödeme bilgisi
        ziyaret_ids  = [z.id for z in ziyaretler]
        tooth_records = {}
        if ziyaret_ids:
            try:
                for tr in ToothRecord.objects.filter(visit_id__in=ziyaret_ids):
                    tooth_records.setdefault(tr.visit_id, []).append(tr)
            except Exception:
                pass

        # İstatistikler
        toplam_randevu  = len(randevular)
        toplam_ziyaret  = len(ziyaretler)
        toplam_odeme    = sum(z.fee or 0 for z in ziyaretler if z.is_paid)
        bekleyen_randevu = sum(1 for r in randevular if r.status in ['bekliyor', 'onaylandi'])

        # Klinikler listesi
        klinikler = list({r.clinic for r in randevular if hasattr(r, 'clinic') and r.clinic})

    from patients.models import HastaUser as HU
    return render(request, 'hasta/profil.html', {
        'hasta_user':       hasta_user,
        'randevular':       randevular,
        'ziyaretler':       ziyaretler,
        'tooth_records':    tooth_records,
        'toplam_randevu':   toplam_randevu,
        'toplam_ziyaret':   toplam_ziyaret,
        'toplam_odeme':     toplam_odeme,
        'bekleyen_randevu': bekleyen_randevu,
        'klinikler':        klinikler,
        'blood_types':      HU.BLOOD_TYPES,
    })


# ═══════════════════════════════════════════════════════
# RANDEVU İPTAL
# ═══════════════════════════════════════════════════════

@hasta_login_required
def randevu_iptal(request, randevu_id):
    hasta_user = request.hasta_user
    try:
        randevu = Appointment.objects.get(
            id=randevu_id,
            patient__phone_number=hasta_user.phone_number,
            status__in=['bekliyor', 'onaylandi'],
        )
    except Appointment.DoesNotExist:
        messages.error(request, 'Randevu bulunamadı veya iptal edilemez.')
        return redirect(f"{settings.SITE_URL}/hasta/profilim/")

    if request.method == 'POST':
        randevu.status = 'iptal'
        randevu.save()

        # Klinik bildirim
        from patients.models import Notification
        Notification.objects.create(
            clinic=randevu.clinic,
            type='iptal_randevu',
            title='Hasta Randevu İptal Etti',
            body=f'{randevu.patient.name} — {randevu.date_time.strftime("%d.%m.%Y %H:%M")} randevusunu iptal etti.',
        )
        messages.success(request, 'Randevunuz iptal edildi.')
        return redirect(f"{settings.SITE_URL}/hasta/profilim/")

    return render(request, 'hasta/randevu_iptal.html', {
        'hasta_user': hasta_user,
        'randevu':    randevu,
    })