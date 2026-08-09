import random
import string
from datetime import timedelta

from django.db import models
from django.conf import settings
from django.utils import timezone


class Doctor(models.Model):
    SPECIALTIES = [
        ('genel_dis', 'Genel Diş Hekimliği'),
        ('ortodonti', 'Ortodonti'),
        ('implant', 'İmplant'),
        ('cocuk_dis', 'Çocuk Diş Hekimliği'),
        ('periodontoloji', 'Periodontoloji (Diş Eti)'),
        ('endodonti', 'Endodonti (Kanal Tedavisi)'),
        ('agiz_cerrahisi', 'Ağız, Diş ve Çene Cerrahisi'),
        ('protez', 'Protetik Diş Tedavisi'),
        ('dis_beyazlatma', 'Diş Beyazlatma'),
        ('estetik_dis', 'Estetik Diş Hekimliği'),
        ('radyoloji', 'Ağız, Diş ve Çene Radyolojisi'),
    ]

    clinic = models.ForeignKey(
        'tenants.Clinic', on_delete=models.CASCADE,
        related_name='doctors', verbose_name="Klinik",
        null=True, blank=True,
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='doctor_profile',
        verbose_name="Kullanıcı Hesabı"
    )
    npi          = models.CharField(max_length=20, unique=True, verbose_name="Doktor ID")
    name         = models.CharField(max_length=255, verbose_name="Ad Soyad")
    email        = models.EmailField(verbose_name="E-posta")
    phone_number = models.CharField(max_length=20, verbose_name="Telefon")
    specialties  = models.JSONField(default=list, verbose_name="Uzmanlık Alanları")
    photo        = models.ImageField(upload_to='doctors/photos/', null=True, blank=True, verbose_name="Fotoğraf")
    about        = models.TextField(null=True, blank=True, verbose_name="Hakkında")
    is_active    = models.BooleanField(default=True, verbose_name="Aktif")
    login_code   = models.CharField(
        max_length=6, blank=True, default='',
        verbose_name="Giriş Kodu",
        help_text="Doktorun panele giriş için kullandığı 6 haneli kod"
    )
    # 2FA OTP alanları
    login_otp     = models.CharField(max_length=6, blank=True, default='', verbose_name="Giriş OTP")
    login_otp_exp = models.DateTimeField(null=True, blank=True, verbose_name="OTP Son Kullanma")

    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Doktor"
        verbose_name_plural = "Doktorlar"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.login_code:
            self.login_code = self._generate_unique_code()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_unique_code():
        while True:
            code = ''.join(random.choices(string.digits, k=6))
            if not Doctor.objects.filter(login_code=code).exists():
                return code

    def get_specialties_display_list(self):
        lookup = dict(self.SPECIALTIES)
        return [lookup.get(s, s) for s in (self.specialties or [])]


class DoctorSession(models.Model):
    """Doktor giriş session'ları — token tabanlı auth"""
    doctor      = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='sessions')
    token       = models.CharField(max_length=64, unique=True)
    remember_me = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    expires_at  = models.DateTimeField()

    class Meta:
        verbose_name = 'Doktor Session'

    def is_valid(self):
        return timezone.now() < self.expires_at

    @classmethod
    def create_for(cls, doctor, remember_me=False):
        token    = ''.join(random.choices(string.ascii_letters + string.digits, k=48))
        duration = timedelta(days=30) if remember_me else timedelta(days=1)
        return cls.objects.create(
            doctor=doctor, token=token,
            remember_me=remember_me,
            expires_at=timezone.now() + duration,
        )