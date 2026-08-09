from django.conf import settings
import json
import datetime as dt_module
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q
from django.core.mail import send_mail

from .models import Doctor, DoctorSession
from patients.models import Patient, Visit, ToothRecord, Appointment, PatientFile, Notification
from tenants.models import Clinic


# ═══════════════════════════════════════════════════════
# YARDIMCI
# ═══════════════════════════════════════════════════════

def get_doktor_from_request(request):
    token = request.COOKIES.get('doktor_token')
    if not token:
        return None
    try:
        session = DoctorSession.objects.select_related('doctor__clinic').get(token=token)
        if session.is_valid():
            return session.doctor
        session.delete()
    except DoctorSession.DoesNotExist:
        pass
    return None


def doktor_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        doktor = get_doktor_from_request(request)
        if not doktor:
            return redirect(f"{settings.PANEL_URL}/doktor/giris/")
        request.doktor = doktor
        return view_func(request, *args, **kwargs)
    return wrapper


ISLEMLER = [
    ('muayene',    'Muayene',        '🔍'),
    ('dolgu',      'Dolgu',          '🦷'),
    ('cekim',      'Çekim',          '🔧'),
    ('kanal',      'Kanal Tedavisi', '💉'),
    ('implant',    'İmplant',        '🔩'),
    ('kron',       'Kron/Köprü',     '👑'),
    ('temizlik',   'Diş Temizliği',  '✨'),
    ('beyazlatma', 'Beyazlatma',     '⭐'),
    ('ortodonti',  'Ortodonti',      '😁'),
    ('protez',     'Protez',         '🦷'),
    ('rontgen',    'Röntgen',        '🩻'),
    ('diger',      'Diğer',          '📋'),
]

import random, string

def _otp_gonder(doktor):
    """Doktor email'ine 6 haneli OTP gönder"""
    otp = ''.join(random.choices(string.digits, k=6))
    doktor.login_otp     = otp
    doktor.login_otp_exp = timezone.now() + dt_module.timedelta(minutes=10)
    doktor.save(update_fields=['login_otp', 'login_otp_exp'])
    try:
        send_mail(
            subject='e-Randevu — Doktor Giriş Doğrulama Kodu',
            message=f"Giriş doğrulama kodunuz: {otp}\n\nBu kod 10 dakika geçerlidir.",
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@e-randevu.online'),
            recipient_list=[doktor.email],
            fail_silently=True,
        )
    except Exception:
        pass
    return otp


# ═══════════════════════════════════════════════════════
# GİRİŞ / ÇIKIŞ — 2 ADIMLI
# ═══════════════════════════════════════════════════════

def doktor_giris(request):
    doktor = get_doktor_from_request(request)
    if doktor:
        return redirect(f"{settings.PANEL_URL}/doktor/{doktor.clinic.clinic_id}/dashboard/")

    # ── ADIM 2: OTP doğrulama ──
    if request.method == 'POST' and request.POST.get('step') == 'otp':
        otp_girilen = request.POST.get('otp', '').strip()
        doktor_id   = request.session.get('doktor_giris_id')
        remember_me = request.session.get('doktor_remember', False)

        if not doktor_id:
            messages.error(request, 'Oturum süresi doldu.')
            return render(request, 'doktor/giris.html', {'step': 'giris'})

        try:
            doktor = Doctor.objects.select_related('clinic').get(id=doktor_id)
        except Doctor.DoesNotExist:
            messages.error(request, 'Doktor bulunamadı.')
            return render(request, 'doktor/giris.html', {'step': 'giris'})

        # OTP kontrol
        if (hasattr(doktor, 'login_otp') and
                doktor.login_otp == otp_girilen and
                doktor.login_otp_exp and
                timezone.now() < doktor.login_otp_exp):
            # Temizle
            doktor.login_otp = ''
            doktor.login_otp_exp = None
            doktor.save(update_fields=['login_otp', 'login_otp_exp'])

            session  = DoctorSession.create_for(doktor, remember_me=remember_me)
            response = redirect(f"{settings.PANEL_URL}/doktor/{doktor.clinic.clinic_id}/dashboard/")
            max_age  = 30 * 24 * 3600 if remember_me else None
            response.set_cookie('doktor_token', session.token, max_age=max_age, httponly=True, samesite='Lax')
            request.session.pop('doktor_giris_id', None)
            request.session.pop('doktor_remember', None)
            return response
        else:
            messages.error(request, '❌ Kod hatalı veya süresi dolmuş.')
            return render(request, 'doktor/giris.html', {
                'step': 'otp',
                'email': request.session.get('doktor_email', ''),
            })

    # ── ADIM 1: Kod + email ile giriş ──
    if request.method == 'POST':
        email       = request.POST.get('email', '').strip().lower()
        kod         = request.POST.get('kod', '').strip()
        remember_me = request.POST.get('remember_me') == 'on'

        try:
            doktor = Doctor.objects.select_related('clinic').get(
                email__iexact=email, login_code=kod, is_active=True,
            )
        except Doctor.DoesNotExist:
            messages.error(request, '❌ E-posta veya giriş kodu hatalı.')
            return render(request, 'doktor/giris.html', {'step': 'giris', 'email': email})

        # Email doğrulama kodu gönder
        if doktor.email:
            _otp_gonder(doktor)
            request.session['doktor_giris_id'] = doktor.id
            request.session['doktor_remember']  = remember_me
            request.session['doktor_email']     = email
            return render(request, 'doktor/giris.html', {
                'step': 'otp',
                'email': email,
            })
        else:
            # Email yoksa direkt giriş
            session  = DoctorSession.create_for(doktor, remember_me=remember_me)
            response = redirect(f"{settings.PANEL_URL}/doktor/{doktor.clinic.clinic_id}/dashboard/")
            max_age  = 30 * 24 * 3600 if remember_me else None
            response.set_cookie('doktor_token', session.token, max_age=max_age, httponly=True, samesite='Lax')
            return response

    return render(request, 'doktor/giris.html', {'step': 'giris'})


def doktor_kod(request):
    return redirect(f"{settings.PANEL_URL}/doktor/giris/")


def doktor_cikis(request):
    token = request.COOKIES.get('doktor_token')
    if token:
        DoctorSession.objects.filter(token=token).delete()
    response = redirect(f"{settings.PANEL_URL}/doktor/giris/")
    response.delete_cookie('doktor_token')
    return response


# ═══════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════

@doktor_login_required
def doktor_dashboard(request, clinic_id):
    from django_tenants.utils import schema_context
    doktor   = request.doktor
    bugun    = timezone.now().date()
    local_tz = timezone.get_current_timezone()

    with schema_context('public'):
        bugun_randevular = list(Appointment.objects.filter(
            doctor=doktor, date_time__date=bugun,
        ).select_related('patient').order_by('date_time'))

        tum_randevular = list(Appointment.objects.filter(
            doctor=doktor,
            date_time__gte=timezone.now() - dt_module.timedelta(days=7),
        ).select_related('patient').order_by('date_time'))

        bekleyen = Appointment.objects.filter(
            doctor=doktor, status='bekliyor'
        ).count()

    toplam_hasta  = Patient.objects.filter(clinic__clinic_id=clinic_id).count()
    bu_ay_ziyaret = Visit.objects.filter(
        doctor=doktor,
        date_time__year=timezone.now().year,
        date_time__month=timezone.now().month,
    ).count()

    takvim_data = []
    for r in tum_randevular:
        renk = {
            'bekliyor':'#f59e0b','onaylandi':'#2563eb',
            'tamamlandi':'#16a34a','tamamlanamadi':'#f97316','iptal':'#dc2626',
        }.get(r.status, '#6b7280')
        bitis    = r.date_time + dt_module.timedelta(minutes=r.duration)
        dt_local = r.date_time.astimezone(local_tz)
        dt_bit   = bitis.astimezone(local_tz)
        takvim_data.append({
            'id': str(r.id),
            'title': r.patient.name,
            'start': dt_local.strftime('%Y-%m-%dT%H:%M:%S'),
            'end':   dt_bit.strftime('%Y-%m-%dT%H:%M:%S'),
            'backgroundColor': renk, 'borderColor': renk,
            'extendedProps': {
                'hasta_adi': r.patient.name,
                'status': r.status,
                'procedure_label': r.get_procedure_display(),
                'hasta_id': r.patient.id,
            }
        })

    return render(request, 'doktor/dashboard.html', {
        'doktor': doktor, 'clinic_id': clinic_id,
        'bugun_randevular': bugun_randevular,
        'bugun': bugun, 'toplam_hasta': toplam_hasta,
        'bu_ay_ziyaret': bu_ay_ziyaret, 'bekleyen': bekleyen,
        'takvim_json': json.dumps(takvim_data, ensure_ascii=False, default=str),
    })


# ═══════════════════════════════════════════════════════
# RANDEVULAR — silme + tamamlandı → ziyaret
# ═══════════════════════════════════════════════════════

@doktor_login_required
def doktor_randevular(request, clinic_id):
    from django_tenants.utils import schema_context
    doktor = request.doktor

    if request.method == 'POST':
        action     = request.POST.get('action', 'guncelle')
        randevu_id = request.POST.get('randevu_id')

        with schema_context('public'):
            try:
                r = Appointment.objects.select_related('patient').get(id=randevu_id, doctor=doktor)
            except Appointment.DoesNotExist:
                messages.error(request, 'Randevu bulunamadı.')
                return redirect(f"{settings.PANEL_URL}/doktor/{clinic_id}/randevular/")

            if action == 'sil':
                r.delete()
                messages.success(request, '🗑 Randevu silindi.')

            elif action == 'guncelle':
                yeni_status = request.POST.get('status')
                if yeni_status in ['bekliyor','onaylandi','tamamlandi','tamamlanamadi','iptal']:
                    r.status = yeni_status
                    r.save()

                    # Tamamlandı → otomatik ziyaret oluştur
                    if yeni_status == 'tamamlandi':
                        ziyaret = Visit.objects.create(
                            patient=r.patient,
                            doctor=doktor,
                            date_time=r.date_time,
                            procedures=[r.procedure] if r.procedure else [],
                            complaint='',
                            notes='Randevudan otomatik oluşturuldu.',
                            fee=0,
                            is_paid=False,
                        )
                        r.delete()
                        messages.success(request, f'✅ Randevu tamamlandı, ziyaret oluşturuldu.')
                        return redirect(f"{settings.PANEL_URL}/doktor/{clinic_id}/hastalar/{r.patient.id}/ziyaret/{ziyaret.id}/duzenle/")
                    elif yeni_status == 'iptal':
                        r.delete()
                        messages.success(request, '❌ Randevu iptal edildi.')
                    else:
                        messages.success(request, '✅ Randevu durumu güncellendi.')

        return redirect(f"{settings.PANEL_URL}/doktor/{clinic_id}/randevular/")

    with schema_context('public'):
        randevular = list(Appointment.objects.filter(
            doctor=doktor,
        ).select_related('patient').order_by('date_time'))

    return render(request, 'doktor/randevular.html', {
        'doktor': doktor, 'clinic_id': clinic_id,
        'randevular': randevular, 'status_choices': Appointment.STATUS_CHOICES,
    })


# ═══════════════════════════════════════════════════════
# HASTALAR
# ═══════════════════════════════════════════════════════

@doktor_login_required
def doktor_hastalar(request, clinic_id):
    doktor   = request.doktor
    arama    = request.GET.get('q', '').strip()
    hastalar = Patient.objects.filter(clinic__clinic_id=clinic_id, status='aktif').order_by('name')
    if arama:
        hastalar = hastalar.filter(Q(name__icontains=arama)|Q(phone_number__icontains=arama))

    if request.method == 'POST':
        name  = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        if name and phone:
            clinic = Clinic.objects.get(clinic_id=clinic_id)
            Patient.objects.create(
                clinic=clinic, name=name, phone_number=phone,
                email=request.POST.get('email',''),
                gender=request.POST.get('gender','D'),
                blood_type=request.POST.get('blood_type','bilinmiyor'),
            )
            messages.success(request, f'{name} eklendi.')
        return redirect(f"{settings.PANEL_URL}/doktor/{clinic_id}/hastalar/")

    return render(request, 'doktor/hastalar.html', {
        'doktor': doktor, 'clinic_id': clinic_id,
        'hastalar': hastalar, 'arama': arama,
        'gender_choices': Patient.GENDER_CHOICES,
        'blood_types': Patient.BLOOD_TYPES,
    })


# ═══════════════════════════════════════════════════════
# HASTA DETAY — bilgi düzenleme eklendi
# ═══════════════════════════════════════════════════════

@doktor_login_required
def doktor_hasta_detay(request, clinic_id, hasta_id):
    from patients.models import ToothSnapshot
    doktor        = request.doktor
    hasta         = get_object_or_404(Patient, id=hasta_id, clinic__clinic_id=clinic_id)
    ziyaretler    = hasta.visits.all().order_by('-date_time')
    dosyalar      = hasta.files.all().order_by('-uploaded_at')

    # Snapshot sistemi
    snapshots = ToothSnapshot.objects.filter(patient=hasta).order_by('snapshot_date')
    snapshot_id = request.GET.get('snapshot_id')
    if snapshot_id:
        try:
            aktif_snapshot = ToothSnapshot.objects.get(id=snapshot_id, patient=hasta)
        except ToothSnapshot.DoesNotExist:
            aktif_snapshot = snapshots.last()
    else:
        aktif_snapshot = snapshots.last()

    if aktif_snapshot:
        dis_kayitlari = {tr.tooth_number: tr for tr in aktif_snapshot.records.all()}
    else:
        dis_kayitlari = {tr.tooth_number: tr for tr in hasta.tooth_records.all()}

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'hasta_duzenle':
            hasta.name           = request.POST.get('name', hasta.name).strip()
            hasta.phone_number   = request.POST.get('phone_number', hasta.phone_number).strip()
            hasta.email          = request.POST.get('email', '').strip()
            hasta.gender         = request.POST.get('gender', hasta.gender)
            hasta.blood_type     = request.POST.get('blood_type', hasta.blood_type)
            hasta.birth_date     = request.POST.get('birth_date') or hasta.birth_date
            hasta.city           = request.POST.get('city', '').strip()
            hasta.address        = request.POST.get('address', '').strip()
            hasta.allergies      = request.POST.get('allergies', '').strip()
            hasta.medical_notes  = request.POST.get('medical_notes', '').strip()
            hasta.notes          = request.POST.get('notes', '').strip()
            hasta.status         = request.POST.get('status', hasta.status)
            hasta.save()
            messages.success(request, '✅ Hasta bilgileri güncellendi.')

        elif action == 'dis_guncelle':
            tooth_number = int(request.POST.get('tooth_number'))
            ToothRecord.objects.update_or_create(
                patient=hasta, tooth_number=tooth_number,
                defaults={'status': request.POST.get('status'), 'notes': request.POST.get('notes','')}
            )
            messages.success(request, 'Diş durumu güncellendi.')

        elif action == 'ziyaret_ekle':
            procedures = request.POST.getlist('procedures')
            other = request.POST.get('other_procedure','').strip()
            if other:
                procedures.append(other)
            Visit.objects.create(
                patient=hasta, doctor=doktor,
                date_time=request.POST.get('date_time') or timezone.now(),
                procedures=procedures,
                complaint=request.POST.get('complaint',''),
                notes=request.POST.get('notes',''),
                fee=request.POST.get('fee') or 0,
                is_paid=request.POST.get('is_paid') == 'on',
            )
            messages.success(request, 'Ziyaret eklendi.')

        elif action == 'dosya_yukle':
            if request.FILES.get('file'):
                PatientFile.objects.create(
                    patient=hasta,
                    file=request.FILES['file'],
                    file_type=request.POST.get('file_type','diger'),
                    description=request.POST.get('description',''),
                )
                messages.success(request, 'Dosya yüklendi.')

        return redirect(f"{settings.PANEL_URL}/doktor/{clinic_id}/hastalar/{hasta_id}/")

    return render(request, 'doktor/hasta_detay.html', {
        'doktor': doktor, 'clinic_id': clinic_id,
        'hasta': hasta, 'ziyaretler': ziyaretler,
        'dosyalar': dosyalar,
        'dis_kayitlari': dis_kayitlari,
        'tooth_statuses': ToothRecord.TOOTH_STATUS,
        'islemler': ISLEMLER,
        'gender_choices': Patient.GENDER_CHOICES,
        'blood_types': Patient.BLOOD_TYPES,
        'status_choices': Patient.STATUS_CHOICES if hasattr(Patient, 'STATUS_CHOICES') else [('aktif','Aktif'),('pasif','Pasif')],
        'snapshots': snapshots,
        'aktif_snapshot': aktif_snapshot,
    })


# ═══════════════════════════════════════════════════════
# ZİYARET DÜZENLE — fiyat alanı kaldırıldı (sadece işlem)
# ═══════════════════════════════════════════════════════

@doktor_login_required
def doktor_ziyaret_duzenle(request, clinic_id, hasta_id, ziyaret_id):
    doktor    = request.doktor
    hasta     = get_object_or_404(Patient, id=hasta_id, clinic__clinic_id=clinic_id)
    ziyaret   = get_object_or_404(Visit, id=ziyaret_id, patient=hasta)
    doktorlar = Doctor.objects.filter(clinic__clinic_id=clinic_id, is_active=True)

    if request.method == 'POST':
        procedures = request.POST.getlist('procedures')
        other = request.POST.get('other_procedure','').strip()
        if other:
            procedures.append(other)
        ziyaret.doctor_id  = request.POST.get('doctor') or doktor.id
        ziyaret.date_time  = request.POST.get('date_time') or ziyaret.date_time
        ziyaret.procedures = procedures
        ziyaret.complaint  = request.POST.get('complaint','')
        ziyaret.notes      = request.POST.get('notes','')
        # Fiyat doktor tarafından girilmez — klinik yönetir
        ziyaret.save()
        messages.success(request, '✅ Ziyaret güncellendi.')
        return redirect(f"{settings.PANEL_URL}/doktor/{clinic_id}/hastalar/{hasta_id}/")

    return render(request, 'doktor/ziyaret_duzenle.html', {
        'doktor': doktor, 'clinic_id': clinic_id,
        'hasta': hasta, 'ziyaret': ziyaret,
        'doktorlar': doktorlar,
        'islemler': ISLEMLER,
        'from_randevu': False,
    })


# ═══════════════════════════════════════════════════════
# BİLDİRİM API
# ═══════════════════════════════════════════════════════

@doktor_login_required
def doktor_bildirim_listesi(request, clinic_id):
    from django_tenants.utils import schema_context
    doktor = request.doktor
    with schema_context('public'):
        bildirimler = list(Notification.objects.filter(
            clinic__clinic_id=clinic_id,
            is_read=False,
        ).filter(
            Q(body__icontains=doktor.name)
        ).order_by('-created_at')[:20])

    data = [{'id':b.id,'type':b.type,'title':b.title,'body':b.body,
             'created_at':b.created_at.strftime('%H:%M')} for b in bildirimler]
    return JsonResponse({'notifications': data})


@doktor_login_required
def doktor_bildirim_okundu(request, clinic_id):
    if request.method == 'POST':
        import json as _json
        ids = _json.loads(request.body).get('ids', [])
        Notification.objects.filter(clinic__clinic_id=clinic_id, id__in=ids).update(is_read=True)
    return JsonResponse({'ok': True})


# ═══════════════════════════════════════════════════════
# BİLDİRİMLER SAYFA
# ═══════════════════════════════════════════════════════

@doktor_login_required
def doktor_bildirimler(request, clinic_id):
    doktor = request.doktor
    # Sadece bu doktora ait bildirimleri göster
    # body'de doktorun adı geçiyor veya doctor field'ı bu doktor
    with __import__('django_tenants.utils', fromlist=['schema_context']).schema_context('public'):
        bildirimler = list(Notification.objects.filter(
            clinic__clinic_id=clinic_id,
        ).filter(
            Q(body__icontains=doktor.name)
        ).order_by('-created_at')[:100])
    return render(request, 'doktor/bildirimler.html', {
        'doktor': doktor, 'clinic_id': clinic_id,
        'bildirimler': bildirimler,
    })


# ═══════════════════════════════════════════════════════
# SNAPSHOT (DİŞ HARİTASI)
# ═══════════════════════════════════════════════════════

@doktor_login_required
def doktor_snapshot_ekle(request, clinic_id, hasta_id):
    from patients.models import ToothSnapshot, ToothRecord as TR
    if request.method != 'POST':
        return redirect(f"{settings.PANEL_URL}/doktor/{clinic_id}/hastalar/{hasta_id}/")
    hasta = get_object_or_404(Patient, id=hasta_id, clinic__clinic_id=clinic_id)
    label = request.POST.get('label', '').strip() or 'Yeni Harita'
    snapshot_date = request.POST.get('snapshot_date') or timezone.now().date()
    kopya_id = request.POST.get('kopya_snapshot_id', '').strip()

    snap = ToothSnapshot.objects.create(
        patient=hasta, label=label, snapshot_date=snapshot_date,
    )

    # Kopyala
    if kopya_id:
        try:
            kaynak = ToothSnapshot.objects.get(id=kopya_id, patient=hasta)
            for tr in kaynak.records.all():
                TR.objects.create(
                    patient=hasta, snapshot=snap,
                    tooth_number=tr.tooth_number,
                    status=tr.status, notes=tr.notes,
                )
        except ToothSnapshot.DoesNotExist:
            pass

    messages.success(request, f'✅ "{label}" haritası oluşturuldu.')
    return redirect(f"{settings.PANEL_URL}/doktor/{clinic_id}/hastalar/{hasta_id}/?snapshot_id={snap.id}&tab=dis-haritasi")


@doktor_login_required
def doktor_snapshot_sil(request, clinic_id, hasta_id, snapshot_id):
    from patients.models import ToothSnapshot
    hasta = get_object_or_404(Patient, id=hasta_id, clinic__clinic_id=clinic_id)
    try:
        snap = ToothSnapshot.objects.get(id=snapshot_id, patient=hasta)
        snap.delete()
        messages.success(request, '🗑 Harita silindi.')
    except ToothSnapshot.DoesNotExist:
        messages.error(request, 'Harita bulunamadı.')
    return redirect(f"{settings.PANEL_URL}/doktor/{clinic_id}/hastalar/{hasta_id}/")