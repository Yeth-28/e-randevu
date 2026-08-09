from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta

from tenants.models import Clinic, ClinicCard
from tenants.models import Subscription
from tenants.iyzico import PLANS, odeme_baslat
from patients.models import Patient
from doctors.models import Doctor

# ─── PLAN LİMİTLERİ ──────────────────────────────────────────────

PLAN_LIMITS = {
    'free': {
        'max_doctors': 1,
        'max_patients': 50,
        'label': 'Ücretsiz',
        'color': '#6b7280',
        'bg': '#f3f4f6',
        'next_plan': 'pro',
    },
    'pro': {
        'max_doctors': 5,
        'max_patients': 500,
        'label': 'Pro',
        'color': '#059669',
        'bg': '#dcfce7',
        'next_plan': 'enterprise',
    },
    'enterprise': {
        'max_doctors': 999,
        'max_patients': 99999,
        'label': 'Kurumsal',
        'color': '#7c3aed',
        'bg': '#f3e8ff',
        'next_plan': None,
    },
}

PLAN_DISPLAY = {
    'free':       {'name': 'Ücretsiz Plan',  'emoji': '🆓', 'color': '#6b7280'},
    'pro':        {'name': 'Pro Plan',       'emoji': '💎', 'color': '#059669'},
    'enterprise': {'name': 'Kurumsal Plan',  'emoji': '🏢', 'color': '#7c3aed'},
}


def get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '85.34.78.112')


def _limit_kontrol(clinic):
    """Klinik limitlerini kontrol et, uyarı mesajı döndür"""
    plan   = clinic.plan or 'free'
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS['free'])

    hasta_sayisi  = Patient.objects.filter(clinic=clinic, status='aktif').count()
    doktor_sayisi = Doctor.objects.filter(clinic=clinic, is_active=True).count()

    uyarilar = []
    max_hasta  = limits['max_patients']
    max_doktor = limits['max_doctors']

    # Hasta limiti
    if max_hasta < 99999:
        oran = hasta_sayisi / max_hasta if max_hasta > 0 else 1
        if oran >= 1:
            uyarilar.append({
                'tip': 'kirmizi',
                'mesaj': f'⚠️ Hasta limitinize ({max_hasta}) ulaştınız! Daha fazla hasta ekleyemezsiniz.',
                'sms': f'e-Randevu: {clinic.name} kliniğiniz hasta limitine ({max_hasta}) ulaşmıştır. Üst pakete geçmek için: {settings.PANEL_URL}/{clinic.clinic_id}/abonelik/',
            })
        elif oran >= 0.8:
            uyarilar.append({
                'tip': 'sari',
                'mesaj': f'⚡ Hasta limitinizin %{int(oran*100)}\'ine ulaştınız ({hasta_sayisi}/{max_hasta}). Yakında limit dolacak.',
                'sms': f'e-Randevu: {clinic.name} kliniğiniz hasta limitinin %{int(oran*100)}\'ine ulaştı ({hasta_sayisi}/{max_hasta}). Üst paket: {settings.PANEL_URL}/{clinic.clinic_id}/abonelik/',
            })

    # Doktor limiti
    if max_doktor < 999:
        oran_d = doktor_sayisi / max_doktor if max_doktor > 0 else 1
        if oran_d >= 1:
            uyarilar.append({
                'tip': 'kirmizi',
                'mesaj': f'⚠️ Doktor limitinize ({max_doktor}) ulaştınız!',
                'sms': f'e-Randevu: {clinic.name} doktor limitine ({max_doktor}) ulaştı. Üst paket: {settings.PANEL_URL}/{clinic.clinic_id}/abonelik/',
            })
        elif oran_d >= 0.8:
            uyarilar.append({
                'tip': 'sari',
                'mesaj': f'⚡ Doktor limitinizin %{int(oran_d*100)}\'ine ulaştınız ({doktor_sayisi}/{max_doktor}).',
                'sms': None,
            })

    return {
        'uyarilar': uyarilar,
        'hasta_sayisi': hasta_sayisi,
        'doktor_sayisi': doktor_sayisi,
        'max_hasta': max_hasta,
        'max_doktor': max_doktor,
        'hasta_oran': min(int((hasta_sayisi / max_hasta * 100) if max_hasta < 99999 else 0), 100),
        'doktor_oran': min(int((doktor_sayisi / max_doktor * 100) if max_doktor < 999 else 0), 100),
    }


def _sms_gonder(phone, mesaj):
    """SMS gönder — şimdilik konsola yaz, production'da SMS API'ye bağla"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[SMS] {phone}: {mesaj}")
    # TODO: SMS API entegrasyonu
    # requests.post('https://sms-api.com/send', data={'to': phone, 'msg': mesaj})


def abonelik_planlar(request, clinic_id):
    """Plan seçim + mevcut abonelik + geçmiş + limit uyarıları"""
    clinic = get_object_or_404(Clinic, clinic_id=clinic_id)

    # Aktif abonelik
    aktif_abonelik = Subscription.objects.filter(
        clinic=clinic, status='active'
    ).order_by('-expires_at').first()

    # Abonelik geçmişi
    gecmis = Subscription.objects.filter(
        clinic=clinic
    ).order_by('-created_at')[:20]

    # Limit kontrolü
    limit_bilgi = _limit_kontrol(clinic)

    # Limit uyarıları için SMS gönder (her sayfa yüklemesinde değil, sadece kritik durumlarda)
    for uyari in limit_bilgi['uyarilar']:
        if uyari['tip'] == 'kirmizi' and uyari.get('sms') and clinic.phone:
            # Redis/cache ile tekrar gönderimi önle — basit versiyon: her seferinde gönder
            _sms_gonder(clinic.phone, uyari['sms'])

    # Mevcut plan bilgisi
    mevcut_plan = PLAN_LIMITS.get(clinic.plan or 'free', PLAN_LIMITS['free'])
    next_plan_key = mevcut_plan.get('next_plan')

    return render(request, 'panel/abonelik/planlar.html', {
        'clinic':          clinic,
        'clinic_id':       clinic_id,
        'plans':           PLANS,
        'plan_limits':     PLAN_LIMITS,
        'plan_display':    PLAN_DISPLAY,
        'aktif_abonelik':  aktif_abonelik,
        'gecmis':          gecmis,
        'limit_bilgi':     limit_bilgi,
        'mevcut_plan':     mevcut_plan,
        'next_plan_key':   next_plan_key,
    })


def abonelik_odeme(request, clinic_id, plan_key, period):
    """Ödeme formu — kayıtlı kart seçimi destekli"""
    clinic = get_object_or_404(Clinic, clinic_id=clinic_id)
    plan   = PLANS.get(plan_key)
    if not plan or period not in ('monthly', 'yearly'):
        messages.error(request, 'Geçersiz plan veya periyot.')
        return redirect(f"{settings.PANEL_URL}/{clinic_id}/abonelik/")

    price = plan['yearly_total'] if period == 'yearly' else plan['monthly_price']

    # Kayıtlı kartları al
    try:
        kayitli_kartlar = ClinicCard.objects.filter(clinic=clinic, is_active=True)
    except Exception:
        kayitli_kartlar = []

    if request.method == 'POST':
        kart_tipi = request.POST.get('kart_tipi', 'yeni')  # 'kayitli' veya 'yeni'
        kart_id   = request.POST.get('kayitli_kart_id', '')

        # Kayıtlı kart seçildi
        if kart_tipi == 'kayitli' and kart_id:
            try:
                secilen_kart = ClinicCard.objects.get(id=kart_id, clinic=clinic)
                card_info = {
                    'holder':    secilen_kart.card_holder,
                    'number':    secilen_kart.card_number,
                    'exp_month': secilen_kart.exp_month,
                    'exp_year':  secilen_kart.exp_year,
                    'cvc':       secilen_kart.cvv or '000',
                }
            except ClinicCard.DoesNotExist:
                messages.error(request, 'Seçilen kart bulunamadı.')
                return render(request, 'panel/abonelik/odeme.html', {
                    'clinic': clinic, 'clinic_id': clinic_id,
                    'plan': plan, 'plan_key': plan_key, 'period': period,
                    'price': price, 'kayitli_kartlar': kayitli_kartlar,
                })
        else:
            # Yeni kart bilgileri
            card_info = {
                'holder':    request.POST.get('card_holder', '').strip(),
                'number':    request.POST.get('card_number', '').replace(' ', ''),
                'exp_month': request.POST.get('exp_month', ''),
                'exp_year':  request.POST.get('exp_year', ''),
                'cvc':       request.POST.get('cvc', ''),
            }

        buyer_info = {
            'name':    request.POST.get('buyer_name', clinic.name).strip(),
            'surname': request.POST.get('buyer_surname', '').strip() or 'Sahibi',
            'email':   request.POST.get('buyer_email', clinic.email or request.user.email),
            'phone':   request.POST.get('buyer_phone', clinic.phone or '+905000000000'),
            'city':    request.POST.get('buyer_city', clinic.city or 'İstanbul'),
            'address': request.POST.get('buyer_address', clinic.address or 'Türkiye'),
            'ip':      get_client_ip(request),
        }

        if not card_info['holder'] or not card_info['number'] or not card_info['cvc']:
            messages.error(request, 'Kart bilgilerini eksiksiz girin.')
            return render(request, 'panel/abonelik/odeme.html', {
                'clinic': clinic, 'clinic_id': clinic_id,
                'plan': plan, 'plan_key': plan_key, 'period': period,
                'price': price, 'kayitli_kartlar': kayitli_kartlar,
            })

        result = odeme_baslat(
            clinic=clinic,
            plan_key=plan_key,
            period=period,
            buyer_info=buyer_info,
            card_info=card_info,
            callback_url=f"{settings.PANEL_URL}/{clinic_id}/abonelik/sonuc/",
        )

        if result['success']:
            now = timezone.now()
            expires = now + timedelta(days=365 if period == 'yearly' else 30)

            # Eski aktif abonelikleri pasif yap
            Subscription.objects.filter(clinic=clinic, status='active').update(status='expired')

            Subscription.objects.create(
                clinic=clinic,
                plan=plan_key,
                period=period,
                status='active',
                amount=price,
                iyzico_payment_id=result.get('payment_id', ''),
                iyzico_conversation_id=result.get('conversation_id', ''),
                starts_at=now,
                expires_at=expires,
            )

            clinic.plan = plan_key
            clinic.save(update_fields=['plan'])

            return redirect(
                f"{settings.PANEL_URL}/{clinic_id}/abonelik/basarili/"
                f'?plan={plan_key}&period={period}'
            )
        else:
            messages.error(request, f'Ödeme başarısız: {result["message"]}')

    return render(request, 'panel/abonelik/odeme.html', {
        'clinic':          clinic,
        'clinic_id':       clinic_id,
        'plan':            plan,
        'plan_key':        plan_key,
        'period':          period,
        'price':           price,
        'kayitli_kartlar': kayitli_kartlar,
    })


def abonelik_basarili(request, clinic_id):
    clinic   = get_object_or_404(Clinic, clinic_id=clinic_id)
    plan_key = request.GET.get('plan', '')
    period   = request.GET.get('period', '')
    plan     = PLANS.get(plan_key, {})
    abonelik = Subscription.objects.filter(
        clinic=clinic, status='active'
    ).order_by('-created_at').first()

    return render(request, 'panel/abonelik/basarili.html', {
        'clinic':    clinic,
        'clinic_id': clinic_id,
        'plan':      plan,
        'plan_key':  plan_key,
        'period':    period,
        'abonelik':  abonelik,
    })