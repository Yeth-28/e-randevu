from django.conf import settings
import json
import datetime as dt_module

from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone as tz

from tenants.models import Clinic
from .models import Patient, Visit, PatientFile, ToothRecord, ToothSnapshot, Appointment, PatientToothModel, Notification
from django.http import JsonResponse
from doctors.models import Doctor


def get_clinic(clinic_id):
    return get_object_or_404(Clinic, clinic_id=clinic_id)


# ─────────────────────────────────────────────
# HASTALAR
# ─────────────────────────────────────────────

@login_required
def hasta_listesi(request, clinic_id):
    clinic = get_clinic(clinic_id)
    arama            = request.GET.get('q', '').strip()
    cinsiyet         = request.GET.get('cinsiyet', '')
    durum            = request.GET.get('durum', 'aktif')
    kayit_baslangic  = request.GET.get('kayit_baslangic', '')
    kayit_bitis      = request.GET.get('kayit_bitis', '')

    hastalar = Patient.objects.filter(clinic=clinic)

    if durum:
        hastalar = hastalar.filter(status=durum)
    if arama:
        hastalar = hastalar.filter(
            models.Q(name__icontains=arama) |
            models.Q(phone_number__icontains=arama) |
            models.Q(email__icontains=arama) |
            models.Q(city__icontains=arama)
        )
    if cinsiyet:
        hastalar = hastalar.filter(gender=cinsiyet)
    if kayit_baslangic:
        hastalar = hastalar.filter(created_at__date__gte=kayit_baslangic)
    if kayit_bitis:
        hastalar = hastalar.filter(created_at__date__lte=kayit_bitis)

    hastalar = hastalar.order_by('-created_at')
    toplam = hastalar.count()

    return render(request, 'panel/hastalar/liste.html', {
        'hastalar':         hastalar,
        'clinic_id':        clinic_id,
        'arama':            arama,
        'cinsiyet':         cinsiyet,
        'durum':            durum,
        'kayit_baslangic':  kayit_baslangic,
        'kayit_bitis':      kayit_bitis,
        'toplam':           toplam,
        'gender_choices':   Patient.GENDER_CHOICES,
    })


@login_required
def hasta_ekle(request, clinic_id):
    clinic = get_clinic(clinic_id)
    doktorlar = Doctor.objects.filter(clinic=clinic, is_active=True)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()

        if not name or not phone:
            messages.error(request, 'Ad Soyad ve Telefon zorunludur!')
            return render(request, 'panel/hastalar/ekle.html', {
                'clinic_id': clinic_id,
                'doktorlar': doktorlar,
                'blood_types': Patient.BLOOD_TYPES,
                'gender_choices': Patient.GENDER_CHOICES,
            })

        Patient.objects.create(
            clinic=clinic,
            name=name,
            phone_number=phone,
            email=request.POST.get('email', ''),
            date_of_birth=request.POST.get('dob') or None,
            gender=request.POST.get('gender', 'D'),
            address=request.POST.get('address', ''),
            city=request.POST.get('city', ''),
            blood_type=request.POST.get('blood_type', 'bilinmiyor'),
            allergies=request.POST.get('allergies', ''),
            medical_notes=request.POST.get('medical_notes', ''),
            emergency_contact_name=request.POST.get('emergency_name', ''),
            emergency_contact_phone=request.POST.get('emergency_phone', ''),
            emergency_contact_relation=request.POST.get('emergency_relation', ''),
            insurance_company=request.POST.get('insurance_company', ''),
            insurance_number=request.POST.get('insurance_number', ''),
            notes=request.POST.get('notes', ''),
        )
        messages.success(request, f'{name} başarıyla eklendi!')
        return redirect(f"{settings.PANEL_URL}/{clinic_id}/hastalar/")

    return render(request, 'panel/hastalar/ekle.html', {
        'clinic_id': clinic_id,
        'doktorlar': doktorlar,
        'blood_types': Patient.BLOOD_TYPES,
        'gender_choices': Patient.GENDER_CHOICES,
    })


@login_required
def hasta_detay(request, clinic_id, hasta_id):
    clinic = get_clinic(clinic_id)
    hasta = get_object_or_404(Patient, id=hasta_id, clinic=clinic)
    ziyaretler = hasta.visits.all().order_by('-date_time')
    dosyalar = hasta.files.all().order_by('-uploaded_at')
    doktorlar = Doctor.objects.filter(clinic=clinic, is_active=True)

    snapshots = hasta.tooth_snapshots.all().order_by('snapshot_date')
    snapshot_id = request.GET.get('snapshot_id')
    aktif_snapshot = None
    if snapshot_id:
        aktif_snapshot = snapshots.filter(id=snapshot_id).first()
    if not aktif_snapshot and snapshots.exists():
        aktif_snapshot = snapshots.last()

    if aktif_snapshot:
        dis_kayitlari = {tr.tooth_number: tr for tr in aktif_snapshot.records.all()}
    else:
        dis_kayitlari = {tr.tooth_number: tr for tr in hasta.tooth_records.filter(snapshot__isnull=True)}

    return render(request, 'panel/hastalar/detay.html', {
        'hasta': hasta,
        'clinic_id': clinic_id,
        'ziyaretler': ziyaretler,
        'dosyalar': dosyalar,
        'dis_kayitlari': dis_kayitlari,
        'doktorlar': doktorlar,
        'tooth_statuses': ToothRecord.TOOTH_STATUS,
        'snapshots': snapshots,
        'aktif_snapshot': aktif_snapshot,
        'upper_right': [8, 7, 6, 5, 4, 3, 2, 1],
        'upper_left': [9, 10, 11, 12, 13, 14, 15, 16],
        'lower_right': [32, 31, 30, 29, 28, 27, 26, 25],
        'lower_left': [24, 23, 22, 21, 20, 19, 18, 17],
    })


@login_required
def hasta_duzenle(request, clinic_id, hasta_id):
    clinic = get_clinic(clinic_id)
    hasta = get_object_or_404(Patient, id=hasta_id, clinic=clinic)

    if request.method == 'POST':
        hasta.name = request.POST.get('name', '').strip()
        hasta.phone_number = request.POST.get('phone', '').strip()
        hasta.email = request.POST.get('email', '')
        hasta.date_of_birth = request.POST.get('dob') or None
        hasta.gender = request.POST.get('gender', 'D')
        hasta.address = request.POST.get('address', '')
        hasta.city = request.POST.get('city', '')
        hasta.blood_type = request.POST.get('blood_type', 'bilinmiyor')
        hasta.allergies = request.POST.get('allergies', '')
        hasta.medical_notes = request.POST.get('medical_notes', '')
        hasta.emergency_contact_name = request.POST.get('emergency_name', '')
        hasta.emergency_contact_phone = request.POST.get('emergency_phone', '')
        hasta.emergency_contact_relation = request.POST.get('emergency_relation', '')
        hasta.insurance_company = request.POST.get('insurance_company', '')
        hasta.insurance_number = request.POST.get('insurance_number', '')
        hasta.notes = request.POST.get('notes', '')
        hasta.save()
        messages.success(request, f'{hasta.name} güncellendi!')
        return redirect(f"{settings.PANEL_URL}/{clinic_id}/hastalar/{hasta_id}/")

    return render(request, 'panel/hastalar/duzenle.html', {
        'hasta': hasta,
        'clinic_id': clinic_id,
        'blood_types': Patient.BLOOD_TYPES,
        'gender_choices': Patient.GENDER_CHOICES,
    })


@login_required
def hasta_sil(request, clinic_id, hasta_id):
    clinic = get_clinic(clinic_id)
    hasta = get_object_or_404(Patient, id=hasta_id, clinic=clinic)

    if request.method == 'POST':
        yeni_durum = request.POST.get('durum', 'pasif')
        hasta.status = yeni_durum
        hasta.save()
        if yeni_durum == 'pasif':
            messages.success(request, f'{hasta.name} pasife alındı!')
        else:
            messages.success(request, f'{hasta.name} aktife alındı!')
        return redirect(f"{settings.PANEL_URL}/{clinic_id}/hastalar/")

    return render(request, 'panel/hastalar/sil.html', {
        'hasta': hasta,
        'clinic_id': clinic_id,
    })


@login_required
def ziyaret_ekle(request, clinic_id, hasta_id):
    clinic = get_clinic(clinic_id)
    hasta = get_object_or_404(Patient, id=hasta_id, clinic=clinic)
    doktorlar = Doctor.objects.filter(clinic=clinic, is_active=True)

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

    if request.method == 'POST':
        procedures = request.POST.getlist('procedures')
        other = request.POST.get('other_procedure', '').strip()
        if other:
            procedures.append(other)

        Visit.objects.create(
            patient=hasta,
            doctor_id=request.POST.get('doctor') or None,
            date_time=request.POST.get('date_time'),
            procedures=procedures,
            complaint=request.POST.get('complaint', ''),
            notes=request.POST.get('notes', ''),
            fee=request.POST.get('fee') or 0,
            is_paid=request.POST.get('is_paid') == 'on',
        )
        messages.success(request, 'Ziyaret başarıyla eklendi!')
        return redirect(f"{settings.PANEL_URL}/{clinic_id}/hastalar/{hasta_id}/")

    return render(request, 'panel/hastalar/ziyaret_ekle.html', {
        'hasta': hasta,
        'clinic_id': clinic_id,
        'doktorlar': doktorlar,
        'islemler': ISLEMLER,
        'now': tz.now(),
    })


@login_required
def dis_haritasi_guncelle(request, clinic_id, hasta_id):
    clinic = get_clinic(clinic_id)
    hasta = get_object_or_404(Patient, id=hasta_id, clinic=clinic)

    if request.method == 'POST':
        tooth_number = int(request.POST.get('tooth_number'))
        status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        snapshot_id = request.POST.get('snapshot_id')

        snapshot = None
        if snapshot_id:
            snapshot = ToothSnapshot.objects.filter(id=snapshot_id, patient=hasta).first()

        ToothRecord.objects.update_or_create(
            patient=hasta,
            snapshot=snapshot,
            tooth_number=tooth_number,
            defaults={'status': status, 'notes': notes}
        )

    snap_param = f"?snapshot_id={snapshot_id}&tab=dis-haritasi" if snapshot_id else "?tab=dis-haritasi"
    return redirect(f"{settings.PANEL_URL}/{clinic_id}/hastalar/{hasta_id}/{snap_param}")


@login_required
def dosya_yukle(request, clinic_id, hasta_id):
    clinic = get_clinic(clinic_id)
    hasta = get_object_or_404(Patient, id=hasta_id, clinic=clinic)

    if request.method == 'POST' and request.FILES.get('file'):
        PatientFile.objects.create(
            patient=hasta,
            file=request.FILES['file'],
            file_type=request.POST.get('file_type', 'diger'),
            description=request.POST.get('description', ''),
        )
        messages.success(request, 'Dosya yüklendi!')

    return redirect(f"{settings.PANEL_URL}/{clinic_id}/hastalar/{hasta_id}/")


@login_required
def tooth_model_yukle(request, clinic_id, hasta_id):
    clinic = get_clinic(clinic_id)
    hasta = get_object_or_404(Patient, id=hasta_id, clinic=clinic)

    if request.method == 'POST' and request.FILES.get('model_file'):
        dosya = request.FILES['model_file']
        ext = dosya.name.split('.')[-1].lower()
        format_map = {'stl': 'stl', 'obj': 'obj', 'glb': 'glb', 'gltf': 'glb'}
        file_format = format_map.get(ext, 'glb')

        PatientToothModel.objects.create(
            patient=hasta,
            file=dosya,
            file_format=file_format,
            description=request.POST.get('description', ''),
        )
        messages.success(request, '3D diş modeli yüklendi!')

    return redirect(f"{settings.PANEL_URL}/{clinic_id}/hastalar/{hasta_id}/")


# ─────────────────────────────────────────────
# RANDEVULAR
# ─────────────────────────────────────────────

@login_required
def randevu_listesi(request, clinic_id):
    from django_tenants.utils import schema_context
    clinic = get_clinic(clinic_id)
    durum = request.GET.get('durum', '')
    doktor_id = request.GET.get('doktor', '')

    with schema_context('public'):
        randevular_qs = Appointment.objects.select_related('patient', 'doctor', 'patient__clinic').filter(
            doctor__clinic__clinic_id=clinic_id
        )
        if durum:
            randevular_qs = randevular_qs.filter(status=durum)
        if doktor_id:
            randevular_qs = randevular_qs.filter(doctor_id=doktor_id)
        randevular = list(randevular_qs.order_by('date_time'))

    doktorlar = Doctor.objects.filter(clinic=clinic, is_active=True)
    hastalar = Patient.objects.filter(clinic=clinic, status='aktif').order_by('name')

    local_tz = tz.get_current_timezone()
    takvim_data = []
    for r in randevular:
        renk = {
            'bekliyor':      '#f59e0b',
            'onaylandi':     '#2563eb',
            'tamamlandi':    '#16a34a',
            'tamamlanamadi': '#f97316',
            'iptal':         '#dc2626',
        }.get(r.status, '#6b7280')

        bitis = r.date_time + dt_module.timedelta(minutes=r.duration)
        dt_local = r.date_time.astimezone(local_tz)
        dt_bitis_local = bitis.astimezone(local_tz)

        takvim_data.append({
            'id': str(r.id),
            'title': f"{r.patient.name} — {r.get_procedure_display()}",
            'start': dt_local.strftime('%Y-%m-%dT%H:%M:%S'),
            'end': dt_bitis_local.strftime('%Y-%m-%dT%H:%M:%S'),
            'backgroundColor': renk,
            'borderColor': renk,
            'extendedProps': {
                'hasta_adi': r.patient.name,
                'patient_id': r.patient.id,
                'status': r.status,
                'procedure': r.procedure,
                'procedure_label': r.get_procedure_display(),
                'date_time_local': dt_local.strftime('%Y-%m-%dT%H:%M'),
                'duration': r.duration,
                'notes': r.notes,
                'fee': str(r.fee),
                'doctor': r.doctor.name if r.doctor else '',
                'doctor_id': r.doctor_id or '',
            }
        })

    return render(request, 'panel/randevular/liste.html', {
        'clinic_id': clinic_id,
        'randevular': randevular,
        'doktorlar': doktorlar,
        'hastalar': hastalar,
        'durum': durum,
        'doktor_id': doktor_id,
        'takvim_json': json.dumps(takvim_data, ensure_ascii=False, default=str),
        'status_choices': Appointment.STATUS_CHOICES,
        'procedure_choices': Appointment.PROCEDURE_CHOICES,
    })


@login_required
def randevu_ekle(request, clinic_id):
    clinic = get_clinic(clinic_id)
    hastalar = Patient.objects.filter(clinic=clinic, status='aktif').order_by('name')
    doktorlar = Doctor.objects.filter(clinic=clinic, is_active=True)

    if request.method == 'POST':
        from django_tenants.utils import schema_context
        with schema_context('public'):
            Appointment.objects.create(
                patient_id=request.POST.get('patient'),
                doctor_id=request.POST.get('doctor') or None,
                date_time=request.POST.get('date_time'),
                duration=request.POST.get('duration', 30),
                procedure=request.POST.get('procedure', 'muayene'),
                notes=request.POST.get('notes', ''),
                fee=request.POST.get('fee') or 0,
                status='bekliyor',
            )
            hasta_obj = Patient.objects.filter(id=request.POST.get('patient')).first()
        if hasta_obj:
            Notification.objects.create(
                clinic=clinic,
                type='yeni_randevu',
                title='📅 Yeni Randevu',
                body=f'{hasta_obj.name} için yeni randevu oluşturuldu.',
            )
        messages.success(request, 'Randevu oluşturuldu!')
        return redirect(f"{settings.PANEL_URL}/{clinic_id}/randevular/")

    default_dt = request.GET.get('dt', '')

    return render(request, 'panel/randevular/ekle.html', {
        'clinic_id': clinic_id,
        'hastalar': hastalar,
        'doktorlar': doktorlar,
        'procedure_choices': Appointment.PROCEDURE_CHOICES,
        'default_dt': default_dt,
    })


@login_required
def randevu_guncelle(request, clinic_id, randevu_id):
    from django_tenants.utils import schema_context
    clinic  = get_clinic(clinic_id)
    with schema_context('public'):
        randevu = get_object_or_404(Appointment, id=randevu_id)

    if request.method == 'POST':
        eski_status = randevu.status
        yeni_status = request.POST.get('status', randevu.status)

        randevu.status     = yeni_status
        randevu.notes      = request.POST.get('notes', randevu.notes)
        randevu.fee        = request.POST.get('fee') or randevu.fee
        randevu.doctor_id  = request.POST.get('doctor') or None
        randevu.patient_id = request.POST.get('patient') or randevu.patient_id
        randevu.procedure  = request.POST.get('procedure') or randevu.procedure
        randevu.duration   = request.POST.get('duration') or randevu.duration
        dt_val = request.POST.get('date_time')
        if dt_val:
            randevu.date_time = dt_val

        with schema_context('public'):
            # ── İPTAL / TAMAMLANAMADI → randevuyu sil ──
            if yeni_status in ('iptal', 'tamamlanamadi'):
                randevu.delete()
                messages.warning(request, 'Randevu silindi.')
                return redirect(f"{settings.PANEL_URL}/{clinic_id}/randevular/")

            # ── TAMAMLANDI → ziyaret oluştur ──
            if yeni_status == 'tamamlandi' and eski_status != 'tamamlandi':
                hasta_id   = randevu.patient_id
                doktor_id  = randevu.doctor_id
                procedure  = randevu.procedure
                notes      = randevu.notes or ''
                tarih      = randevu.date_time
                procedures = [procedure] if procedure else []

                ziyaret = Visit.objects.create(
                    patient_id=hasta_id,
                    doctor_id=doktor_id,
                    date_time=tarih,
                    procedures=procedures,
                    complaint='',
                    notes=notes,
                    fee=0,
                    is_paid=False,
                )
                randevu.delete()
                messages.success(request, '✅ Randevu tamamlandı, ziyaret olarak kaydedildi.')
                return redirect(f"{settings.PANEL_URL}/{clinic_id}/randevular/")

            randevu.save()
            messages.success(request, 'Randevu güncellendi!')

    return redirect(f"{settings.PANEL_URL}/{clinic_id}/randevular/")


@login_required
def randevu_sil(request, clinic_id, randevu_id):
    from django_tenants.utils import schema_context
    clinic  = get_clinic(clinic_id)

    if request.method == 'POST':
        with schema_context('public'):
            randevu   = get_object_or_404(Appointment, id=randevu_id)
            hasta_adi = randevu.patient.name
            randevu.delete()
        Notification.objects.create(
            clinic=clinic,
            type='iptal_randevu',
            title='❌ Randevu İptal',
            body=f'{hasta_adi} adlı hastanın randevusu iptal edildi.',
        )
        messages.warning(request, 'Randevu silindi.')

    return redirect(f"{settings.PANEL_URL}/{clinic_id}/randevular/")


# ─────────────────────────────────────────────
# ZİYARET DÜZENLE (randevu → ziyaret sonrası ücret girişi)
# ─────────────────────────────────────────────

@login_required
def ziyaret_duzenle(request, clinic_id, hasta_id, ziyaret_id):
    clinic  = get_clinic(clinic_id)
    hasta   = get_object_or_404(Patient, id=hasta_id, clinic=clinic)
    ziyaret = get_object_or_404(Visit, id=ziyaret_id, patient=hasta)
    doktorlar = Doctor.objects.filter(clinic=clinic, is_active=True)

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

    if request.method == 'POST':
        procedures = request.POST.getlist('procedures')
        other = request.POST.get('other_procedure', '').strip()
        if other:
            procedures.append(other)

        ziyaret.doctor_id  = request.POST.get('doctor') or None
        ziyaret.date_time  = request.POST.get('date_time') or ziyaret.date_time
        ziyaret.procedures = procedures
        ziyaret.complaint  = request.POST.get('complaint', '')
        ziyaret.notes      = request.POST.get('notes', '')
        ziyaret.fee        = request.POST.get('fee') or 0
        ziyaret.is_paid    = request.POST.get('is_paid') == 'on'
        ziyaret.save()

        messages.success(request, '✅ Ziyaret kaydedildi!')
        return redirect(f"{settings.PANEL_URL}/{clinic_id}/hastalar/{hasta_id}/?tab=ziyaretler")

    return render(request, 'panel/hastalar/ziyaret_duzenle.html', {
        'hasta':    hasta,
        'ziyaret':  ziyaret,
        'clinic_id': clinic_id,
        'doktorlar': doktorlar,
        'islemler':  ISLEMLER,
        'from_randevu': True,  # template'de "Randevudan oluşturuldu" notu göstermek için
    })


# ─────────────────────────────────────────────
# BİLDİRİM API
# ─────────────────────────────────────────────

@login_required
def bildirim_listesi(request, clinic_id):
    """Okunmamış bildirimleri döndürür — polling için"""
    clinic = get_clinic(clinic_id)
    bildirimler = Notification.objects.filter(clinic=clinic, is_read=False)
    data = [
        {
            'id': b.id,
            'type': b.type,
            'title': b.title,
            'body': b.body,
            'created_at': b.created_at.strftime('%H:%M'),
        }
        for b in bildirimler
    ]
    return JsonResponse({'notifications': data})


@login_required
def bildirim_okundu(request, clinic_id):
    """Bildirimi okundu olarak işaretle"""
    if request.method == 'POST':
        import json as json_module
        data = json_module.loads(request.body)
        ids = data.get('ids', [])
        Notification.objects.filter(clinic__clinic_id=clinic_id, id__in=ids).update(is_read=True)
    return JsonResponse({'ok': True})


@login_required
def bildirim_merkezi(request, clinic_id):
    """Tüm bildirimleri listeleyen sayfa"""
    clinic = get_clinic(clinic_id)
    bildirimler = Notification.objects.filter(clinic=clinic).order_by('-created_at')[:50]
    # Sayfayı açınca hepsini okundu yap
    Notification.objects.filter(clinic=clinic, is_read=False).update(is_read=True)
    return render(request, 'panel/bildirimler.html', {
        'clinic_id': clinic_id,
        'bildirimler': bildirimler,
    })



# ─────────────────────────────────────────────
# DİŞ HARİTASI SNAPSHOT
# ─────────────────────────────────────────────

@login_required
def snapshot_ekle(request, clinic_id, hasta_id):
    clinic = get_clinic(clinic_id)
    hasta = get_object_or_404(Patient, id=hasta_id, clinic=clinic)

    if request.method == 'POST':
        label = request.POST.get('label', 'Yeni Harita').strip() or 'Yeni Harita'
        snapshot_date = request.POST.get('snapshot_date') or tz.now().date()
        kopya_id = request.POST.get('kopya_snapshot_id')

        snapshot = ToothSnapshot.objects.create(
            patient=hasta,
            label=label,
            snapshot_date=snapshot_date,
        )

        if kopya_id:
            kaynak = ToothSnapshot.objects.filter(id=kopya_id, patient=hasta).first()
            if kaynak:
                for record in kaynak.records.all():
                    ToothRecord.objects.create(
                        patient=hasta,
                        snapshot=snapshot,
                        tooth_number=record.tooth_number,
                        status=record.status,
                        notes=record.notes,
                    )

        return redirect(f"{settings.PANEL_URL}/{clinic_id}/hastalar/{hasta_id}/?snapshot_id={snapshot.id}&tab=dis-haritasi")

    return redirect(f"{settings.PANEL_URL}/{clinic_id}/hastalar/{hasta_id}/")


@login_required
def snapshot_sil(request, clinic_id, hasta_id, snapshot_id):
    clinic = get_clinic(clinic_id)
    hasta = get_object_or_404(Patient, id=hasta_id, clinic=clinic)

    if request.method == 'POST':
        ToothSnapshot.objects.filter(id=snapshot_id, patient=hasta).delete()

    return redirect(f"{settings.PANEL_URL}/{clinic_id}/hastalar/{hasta_id}/?tab=dis-haritasi")

# ─────────────────────────────────────────────
# RAPORLAMA
# ─────────────────────────────────────────────

@login_required
def raporlama(request, clinic_id):
    from django_tenants.utils import schema_context
    from django.db.models import Sum, Count
    from django.db.models.functions import TruncMonth, TruncDate, TruncWeek
    import json
    from datetime import timedelta

    clinic = get_clinic(clinic_id)
    bugun  = tz.now().date()
    ay_basi = bugun.replace(day=1)

    # Tarih filtresi
    periyot = request.GET.get('periyot', '12ay')
    if periyot == '3ay':
        baslangic = bugun - timedelta(days=90)
    elif periyot == '6ay':
        baslangic = bugun - timedelta(days=180)
    elif periyot == '30gun':
        baslangic = bugun - timedelta(days=30)
    else:  # 12ay
        baslangic = bugun - timedelta(days=365)

    with schema_context('public'):
        # ── Aylık randevu sayısı ──
        aylik_randevu_qs = Appointment.objects.filter(
            patient__clinic=clinic,
            date_time__date__gte=baslangic,
            status__in=['tamamlandi', 'onaylandi', 'bekliyor'],
        ).annotate(ay=TruncMonth('date_time')).values('ay').annotate(
            sayi=Count('id')
        ).order_by('ay')

        aylik_randevu = {
            'labels': [r['ay'].strftime('%b %Y') for r in aylik_randevu_qs],
            'data':   [r['sayi'] for r in aylik_randevu_qs],
        }

        # ── Aylık gelir ──
        aylik_gelir_qs = Visit.objects.filter(
            patient__clinic=clinic,
            date_time__date__gte=baslangic,
            is_paid=True,
        ).annotate(ay=TruncMonth('date_time')).values('ay').annotate(
            toplam=Sum('fee')
        ).order_by('ay')

        aylik_gelir = {
            'labels': [r['ay'].strftime('%b %Y') for r in aylik_gelir_qs],
            'data':   [float(r['toplam'] or 0) for r in aylik_gelir_qs],
        }

        # ── En çok yapılan işlemler ──
        islem_sayilari = {}
        ziyaretler_all = Visit.objects.filter(
            patient__clinic=clinic,
            date_time__date__gte=baslangic,
        ).values_list('procedures', flat=True)
        for procedures in ziyaretler_all:
            if procedures:
                for p in procedures:
                    islem_sayilari[p] = islem_sayilari.get(p, 0) + 1

        islem_labels_map = {
            'muayene':'Muayene','dolgu':'Dolgu','cekim':'Çekim',
            'kanal':'Kanal','implant':'İmplant','kron':'Kron',
            'temizlik':'Temizlik','beyazlatma':'Beyazlatma',
            'ortodonti':'Ortodonti','protez':'Protez','rontgen':'Röntgen','diger':'Diğer',
        }
        sorted_islemler = sorted(islem_sayilari.items(), key=lambda x: x[1], reverse=True)[:8]
        islem_dagilimi = {
            'labels': [islem_labels_map.get(k, k) for k, v in sorted_islemler],
            'data':   [v for k, v in sorted_islemler],
        }

        # ── Doktor bazlı istatistik ──
        doktor_stats = []
        doktorlar = Doctor.objects.filter(clinic=clinic, is_active=True)
        for d in doktorlar:
            randevu_sayi = Appointment.objects.filter(
                doctor=d,
                patient__clinic=clinic,
                date_time__date__gte=baslangic,
            ).count()
            ziyaret_sayi = Visit.objects.filter(
                doctor=d,
                patient__clinic=clinic,
                date_time__date__gte=baslangic,
            ).count()
            gelir = Visit.objects.filter(
                doctor=d,
                patient__clinic=clinic,
                date_time__date__gte=baslangic,
                is_paid=True,
            ).aggregate(t=Sum('fee'))['t'] or 0
            doktor_stats.append({
                'name': d.name,
                'randevu': randevu_sayi,
                'ziyaret': ziyaret_sayi,
                'gelir': float(gelir),
            })

        # ── Hasta sayısı artışı (aylık yeni hasta) ──
        aylik_hasta_qs = Patient.objects.filter(
            clinic=clinic,
            created_at__date__gte=baslangic,
        ).annotate(ay=TruncMonth('created_at')).values('ay').annotate(
            sayi=Count('id')
        ).order_by('ay')

        aylik_hasta = {
            'labels': [r['ay'].strftime('%b %Y') for r in aylik_hasta_qs],
            'data':   [r['sayi'] for r in aylik_hasta_qs],
        }

        # ── Günlük/haftalık randevu yoğunluğu (son 30 gün) ──
        gunluk_qs = Appointment.objects.filter(
            patient__clinic=clinic,
            date_time__date__gte=bugun - timedelta(days=30),
            status__in=['tamamlandi', 'onaylandi', 'bekliyor'],
        ).annotate(gun=TruncDate('date_time')).values('gun').annotate(
            sayi=Count('id')
        ).order_by('gun')

        gunluk_yogunluk = {
            'labels': [r['gun'].strftime('%d %b') for r in gunluk_qs],
            'data':   [r['sayi'] for r in gunluk_qs],
        }

        # ── Özet kartlar ──
        toplam_hasta    = Patient.objects.filter(clinic=clinic, status='aktif').count()
        bu_ay_randevu   = Appointment.objects.filter(
            patient__clinic=clinic,
            date_time__month=bugun.month,
            date_time__year=bugun.year,
        ).count()
        bu_ay_gelir     = Visit.objects.filter(
            patient__clinic=clinic,
            date_time__month=bugun.month,
            date_time__year=bugun.year,
            is_paid=True,
        ).aggregate(t=Sum('fee'))['t'] or 0
        bu_ay_ziyaret   = Visit.objects.filter(
            patient__clinic=clinic,
            date_time__month=bugun.month,
            date_time__year=bugun.year,
        ).count()

    return render(request, 'panel/raporlama.html', {
        'clinic_id':        clinic_id,
        'periyot':          periyot,
        'toplam_hasta':     toplam_hasta,
        'bu_ay_randevu':    bu_ay_randevu,
        'bu_ay_gelir':      bu_ay_gelir,
        'bu_ay_ziyaret':    bu_ay_ziyaret,
        'aylik_randevu':    json.dumps(aylik_randevu, ensure_ascii=False),
        'aylik_gelir':      json.dumps(aylik_gelir, ensure_ascii=False),
        'islem_dagilimi':   json.dumps(islem_dagilimi, ensure_ascii=False),
        'aylik_hasta':      json.dumps(aylik_hasta, ensure_ascii=False),
        'gunluk_yogunluk':  json.dumps(gunluk_yogunluk, ensure_ascii=False),
        'doktor_stats':     doktor_stats,
    })