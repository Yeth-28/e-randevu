"""
dental/ayarlar_dogrulama_views.py
Klinik Ayarları accordion doğrulama API'si
"""
import json, random, string
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail


def _get_clinic(clinic_id):
    """Clinic'i public schema'dan al"""
    try:
        from django_tenants.utils import schema_context
        with schema_context('public'):
            from tenants.models import Clinic
            return Clinic.objects.get(clinic_id=clinic_id)
    except Exception:
        from tenants.models import Clinic
        return Clinic.objects.get(clinic_id=clinic_id)


def ayarlar_kod_gonder(request, clinic_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Giriş gerekli'}, status=403)

    try:
        clinic = _get_clinic(clinic_id)
    except Exception:
        return JsonResponse({'error': 'Klinik bulunamadı'}, status=404)

    otp = ''.join(random.choices(string.digits, k=6))
    clinic.login_otp     = otp
    clinic.login_otp_exp = timezone.now() + timedelta(minutes=10)
    clinic.save(update_fields=['login_otp', 'login_otp_exp'])

    try:
        send_mail(
            subject='e-Randevu — Klinik Ayarları Doğrulama Kodu',
            message=f"""Klinik Ayarları Doğrulama

{clinic.name} kliniğinin yönetici alanına erişim kodu:

{otp}

Bu kod 10 dakika geçerlidir.
Bu işlemi siz yapmadıysanız güvenlik şifrenizi değiştirin.""",
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@e-randevu.online'),
            recipient_list=[clinic.email],
            fail_silently=True,
        )
    except Exception:
        pass

    email = clinic.email or ''
    parts = email.split('@')
    masked = (parts[0][0] + '***@' + parts[1]) if len(parts) == 2 else email

    return JsonResponse({'ok': True, 'email': masked})


def ayarlar_dogrula_api(request, clinic_id):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Giriş gerekli'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'POST gerekli'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'message': 'Geçersiz istek'})

    otp_girilen = str(data.get('otp', '')).strip()

    try:
        clinic = _get_clinic(clinic_id)
    except Exception:
        return JsonResponse({'success': False, 'message': 'Klinik bulunamadı'})

    if (clinic.login_otp == otp_girilen
            and clinic.login_otp_exp
            and timezone.now() < clinic.login_otp_exp):
        clinic.login_otp = ''
        clinic.login_otp_exp = None
        clinic.save(update_fields=['login_otp', 'login_otp_exp'])
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False, 'message': '❌ Kod hatalı veya süresi dolmuş.'})