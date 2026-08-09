from django_tenants.models import TenantMixin, DomainMixin
from django.db import models
import random
import string
from django.utils.text import slugify
from django.utils import timezone


def generate_clinic_id():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=6))


def generate_subdomain(clinic_name):
    return slugify(clinic_name)


class Clinic(TenantMixin):
    # Temel bilgiler
    name         = models.CharField(max_length=255, verbose_name="Klinik Adı")
    phone_number = models.CharField(max_length=20, blank=True, verbose_name="Telefon")
    email        = models.EmailField(verbose_name="E-posta")
    address      = models.TextField(blank=True, verbose_name="Adres")
    city         = models.CharField(max_length=100, blank=True, verbose_name="Şehir")

    # Benzersiz kimlikler
    clinic_id = models.CharField(
        max_length=6, unique=True, default=generate_clinic_id,
        verbose_name="Klinik ID (6 hane)"
    )
    subdomain = models.CharField(
        max_length=100, unique=True, blank=True,
        verbose_name="Subdomain (ali-klinik)"
    )

    # Abonelik
    PLAN_CHOICES = [
        ('free',       'Ücretsiz'),
        ('basic',      'Basic'),
        ('pro',        'Pro'),
        ('enterprise', 'Enterprise'),
    ]
    plan            = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free', verbose_name="Paket")
    plan_start_date = models.DateField(null=True, blank=True)
    plan_end_date   = models.DateField(null=True, blank=True)
    is_active       = models.BooleanField(default=True, verbose_name="Aktif")
    is_paid         = models.BooleanField(default=False, verbose_name="Ödeme Yapıldı")

    # Klinik ayar bilgileri
    phone        = models.CharField(max_length=20, blank=True, verbose_name="İletişim Telefonu")
    website      = models.URLField(blank=True, verbose_name="Website")
    about        = models.TextField(blank=True, verbose_name="Hakkında")
    logo         = models.ImageField(upload_to='clinics/logos/', null=True, blank=True, verbose_name="Logo")

    # Randevu ayarları
    appointment_duration    = models.IntegerField(default=30, verbose_name="Randevu Süresi (dk)")
    appointment_advance_days = models.IntegerField(default=60, verbose_name="Kaç Gün Önceden Randevu Alınabilir")
    appointment_interval    = models.IntegerField(default=15, verbose_name="Randevu Aralığı (dk)")
    appointments_open       = models.BooleanField(default=True, verbose_name="Online Randevu Açık")

    # Kayıtlı kart bilgileri (sadece last4 + brand saklanır, gerçek kart iyzico'da)
    saved_card_last4        = models.CharField(max_length=4, blank=True, verbose_name="Kart Son 4 Hane")
    saved_card_brand        = models.CharField(max_length=20, blank=True, verbose_name="Kart Markası")
    saved_card_holder       = models.CharField(max_length=100, blank=True, verbose_name="Kart Sahibi")
    saved_card_expiry       = models.CharField(max_length=7, blank=True, verbose_name="Son Kullanma")
    billing_address         = models.TextField(blank=True, verbose_name="Fatura Adresi")
    billing_city            = models.CharField(max_length=100, blank=True, verbose_name="Fatura Şehri")
    billing_zip             = models.CharField(max_length=20, blank=True, verbose_name="Posta Kodu")
    billing_country         = models.CharField(max_length=5, blank=True, default='TR', verbose_name="Ülke")

    # Bildirim ayarları
    sms_notifications     = models.BooleanField(default=False, verbose_name="SMS Bildirimleri")
    email_notifications   = models.BooleanField(default=True, verbose_name="E-posta Bildirimleri")
    reminder_hours_before = models.IntegerField(default=24, verbose_name="Hatırlatma (saat önce)")

    created_at     = models.DateTimeField(auto_now_add=True)

    # Doğrulama & görünürlük
    email_verified = models.BooleanField(default=False, verbose_name="E-posta Doğrulandı")
    phone_verified = models.BooleanField(default=False, verbose_name="Telefon Doğrulandı")
    is_visible     = models.BooleanField(default=False, verbose_name="Arama Motorunda Görünsün")

    # 2FA giriş kodu
    login_otp      = models.CharField(max_length=6, blank=True, default='', verbose_name="Giriş OTP")
    login_otp_exp  = models.DateTimeField(null=True, blank=True, verbose_name="OTP Son Kullanma")
    auto_create_schema = True

    class Meta:
        app_label = 'tenants'
        verbose_name = "Klinik"
        verbose_name_plural = "Klinikler"

    def save(self, *args, **kwargs):
        # Subdomain otomatik oluştur
        if not self.subdomain:
            base = generate_subdomain(self.name)
            subdomain = base
            counter = 1
            while Clinic.objects.filter(subdomain=subdomain).exclude(pk=self.pk).exists():
                subdomain = f"{base}-{counter}"
                counter += 1
            self.subdomain = subdomain

        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Yeni klinik oluşturulunca Domain kayıtlarını otomatik ekle
        if is_new:
            from django.conf import settings
            base_domain = getattr(settings, 'BASE_DOMAIN', 'localhost')

            # Ana hasta subdomain: aliklinik.localhost veya aliklinik.e-randevu.online
            hasta_domain = f"{self.subdomain}.{base_domain}"
            Domain.objects.get_or_create(
                domain=hasta_domain,
                defaults={'tenant': self, 'is_primary': True}
            )

    def __str__(self):
        return f"{self.name} ({self.clinic_id})"


class Domain(DomainMixin):
    class Meta:
        app_label = 'tenants'



class ClinicCard(models.Model):
    """Klinik kayıtlı kartları — çoklu kart desteği"""
    clinic       = models.ForeignKey('Clinic', on_delete=models.CASCADE, related_name='cards')
    last4        = models.CharField(max_length=4, verbose_name="Son 4 Hane")
    brand        = models.CharField(max_length=20, blank=True, verbose_name="Kart Markası")
    holder       = models.CharField(max_length=100, blank=True, verbose_name="Kart Sahibi")
    expiry       = models.CharField(max_length=7, blank=True, verbose_name="Son Kullanma")
    billing_address = models.TextField(blank=True, verbose_name="Fatura Adresi")
    billing_city    = models.CharField(max_length=100, blank=True, verbose_name="Şehir")
    billing_zip     = models.CharField(max_length=20, blank=True, verbose_name="Posta Kodu")
    billing_country = models.CharField(max_length=5, blank=True, default='TR', verbose_name="Ülke")
    is_active    = models.BooleanField(default=False, verbose_name="Aktif Kart")
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Klinik Kartı"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.clinic.name} — {self.brand} •••• {self.last4}"

    def save(self, *args, **kwargs):
        # Aktif yapılırsa diğerlerini pasife al
        if self.is_active:
            ClinicCard.objects.filter(clinic=self.clinic, is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

class Subscription(models.Model):
    PLAN_CHOICES = [
        ('basic',      'Basic'),
        ('pro',        'Pro'),
        ('enterprise', 'Enterprise'),
    ]
    PERIOD_CHOICES = [
        ('monthly', 'Aylık'),
        ('yearly',  'Yıllık'),
    ]
    STATUS_CHOICES = [
        ('active',    'Aktif'),
        ('expired',   'Süresi Dolmuş'),
        ('cancelled', 'İptal Edilmiş'),
        ('pending',   'Bekliyor'),
    ]

    clinic                 = models.ForeignKey('tenants.Clinic', on_delete=models.CASCADE, related_name='subscriptions')
    plan                   = models.CharField(max_length=20, choices=PLAN_CHOICES)
    period                 = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    status                 = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    amount                 = models.DecimalField(max_digits=10, decimal_places=2)
    iyzico_payment_id      = models.CharField(max_length=100, blank=True)
    iyzico_conversation_id = models.CharField(max_length=100, blank=True)
    starts_at              = models.DateTimeField()
    expires_at             = models.DateTimeField()
    created_at             = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Abonelik'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.clinic.name} — {self.get_plan_display()}"

    def is_active_now(self):
        return self.status == 'active' and timezone.now() < self.expires_at

    @property
    def days_remaining(self):
        if self.expires_at > timezone.now():
            return (self.expires_at - timezone.now()).days
        return 0


class ClinicWorkingHours(models.Model):
    DAYS = [
        (0, 'Pazartesi'), (1, 'Salı'),    (2, 'Çarşamba'),
        (3, 'Perşembe'),  (4, 'Cuma'),    (5, 'Cumartesi'), (6, 'Pazar'),
    ]
    clinic     = models.ForeignKey('tenants.Clinic', on_delete=models.CASCADE, related_name='working_hours')
    day        = models.IntegerField(choices=DAYS)
    is_open    = models.BooleanField(default=True)
    open_time  = models.TimeField(default='09:00')
    close_time = models.TimeField(default='18:00')

    class Meta:
        unique_together = ('clinic', 'day')
        ordering = ['day']
        verbose_name = 'Çalışma Saati'

    def __str__(self):
        return f"{self.clinic.name} — {dict(self.DAYS).get(self.day,'')}"


class ClinicHoliday(models.Model):
    clinic       = models.ForeignKey('tenants.Clinic', on_delete=models.CASCADE, related_name='holidays')
    date         = models.DateField()
    description  = models.CharField(max_length=200, blank=True)
    is_recurring = models.BooleanField(default=False)

    class Meta:
        ordering = ['date']
        verbose_name = 'Tatil Günü'

    def __str__(self):
        return f"{self.clinic.name} — {self.date}"


class DoctorWorkingHours(models.Model):
    DAYS = ClinicWorkingHours.DAYS
    doctor     = models.ForeignKey('doctors.Doctor', on_delete=models.CASCADE, related_name='working_hours')
    day        = models.IntegerField(choices=DAYS)
    is_working = models.BooleanField(default=True)
    start_time = models.TimeField(default='09:00')
    end_time   = models.TimeField(default='18:00')

    class Meta:
        unique_together = ('doctor', 'day')
        ordering = ['day']
        verbose_name = 'Doktor Çalışma Saati'

    def __str__(self):
        return f"{self.doctor.name} — {dict(self.DAYS).get(self.day,'')}"