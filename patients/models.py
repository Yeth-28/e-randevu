from django.db import models
from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta
import random
import string
from django.contrib.auth.hashers import make_password, check_password
import secrets


class Patient(models.Model):
    GENDER_CHOICES = [
        ('E', 'Erkek'),
        ('K', 'Kadın'),
        ('D', 'Belirtmek İstemiyorum'),
    ]
    BLOOD_TYPES = [
        ('A+', 'A Rh+'), ('A-', 'A Rh-'),
        ('B+', 'B Rh+'), ('B-', 'B Rh-'),
        ('AB+', 'AB Rh+'), ('AB-', 'AB Rh-'),
        ('0+', '0 Rh+'), ('0-', '0 Rh-'),
        ('bilinmiyor', 'Bilinmiyor'),
    ]
    STATUS_CHOICES = [
        ('aktif', 'Aktif'),
        ('pasif', 'Pasif'),
    ]

    # Klinik bağlantısı
    clinic = models.ForeignKey(
        'tenants.Clinic',
        on_delete=models.CASCADE,
        related_name='patients',
        verbose_name="Klinik",
        null=True,  # mevcut kayıtlar için geçici
        blank=True,
    )

    # Temel bilgiler
    name = models.CharField(max_length=255, verbose_name="Ad Soyad")
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="Doğum Tarihi")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='D', verbose_name="Cinsiyet")
    phone_number = models.CharField(max_length=20, verbose_name="Telefon")
    email = models.EmailField(blank=True, verbose_name="E-posta")
    # photo kaldırıldı

    # Adres
    address = models.TextField(blank=True, verbose_name="Adres")
    city = models.CharField(max_length=100, blank=True, verbose_name="Şehir")

    # Sağlık bilgileri
    blood_type = models.CharField(max_length=10, choices=BLOOD_TYPES, default='bilinmiyor', verbose_name="Kan Grubu")
    allergies = models.TextField(blank=True, verbose_name="Alerjiler")
    medical_notes = models.TextField(blank=True, verbose_name="Tıbbi Notlar")

    # Acil iletişim
    emergency_contact_name = models.CharField(max_length=255, blank=True, verbose_name="Acil Kişi Adı")
    emergency_contact_phone = models.CharField(max_length=20, blank=True, verbose_name="Acil Kişi Telefonu")
    emergency_contact_relation = models.CharField(max_length=100, blank=True, verbose_name="Yakınlık Derecesi")

    # Sigorta
    insurance_company = models.CharField(max_length=255, blank=True, verbose_name="Sigorta Şirketi")
    insurance_number = models.CharField(max_length=100, blank=True, verbose_name="Sigorta No")

    # Durum
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='aktif', verbose_name="Durum")
    notes = models.TextField(blank=True, verbose_name="Notlar")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Hasta"
        verbose_name_plural = "Hastalar"
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_age(self):
        if not self.date_of_birth:
            return None
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

class ToothSnapshot(models.Model):
    """Diş haritası zaman damgası"""
    patient       = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='tooth_snapshots')
    label         = models.CharField(max_length=100, verbose_name="Etiket", default='İlk Muayene')
    snapshot_date = models.DateField(verbose_name="Tarih")
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['snapshot_date']
        verbose_name = "Diş Haritası"

    def __str__(self):
        return f"{self.patient.name} — {self.label} ({self.snapshot_date})"
    

class ToothRecord(models.Model):
    TOOTH_STATUS = [
        ('saglikli', 'Sağlıklı'),
        ('dolgulu', 'Dolgulu'),
        ('cekimli', 'Çekilmiş'),
        ('implant', 'İmplant'),
        ('kanal', 'Kanal Tedavisi'),
        ('kron', 'Kron'),
        ('hasarli', 'Hasarlı/Çürük'),
        ('eksik', 'Eksik (Doğuştan)'),
    ]

    patient      = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='tooth_records')
    snapshot     = models.ForeignKey(ToothSnapshot, on_delete=models.CASCADE, related_name='records', null=True, blank=True)
    tooth_number = models.IntegerField(verbose_name="Diş Numarası")
    status       = models.CharField(max_length=20, choices=TOOTH_STATUS, default='saglikli')
    notes        = models.TextField(blank=True, verbose_name="Not")
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['patient', 'snapshot', 'tooth_number']
        verbose_name = "Diş Kaydı"

    def __str__(self):
        return f"{self.patient.name} - Diş {self.tooth_number}"


class Visit(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='visits')
    doctor = models.ForeignKey('doctors.Doctor', on_delete=models.SET_NULL, null=True, blank=True)
    date_time = models.DateTimeField(verbose_name="Ziyaret Tarihi")
    procedures = models.JSONField(default=list, verbose_name="Yapılan İşlemler")
    complaint = models.TextField(blank=True, verbose_name="Şikayet")  # YENİ
    notes = models.TextField(blank=True, verbose_name="Notlar")
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ücret")
    is_paid = models.BooleanField(default=False, verbose_name="Ödendi mi?")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ziyaret"
        ordering = ['-date_time']

    def __str__(self):
        return f"{self.patient.name} - {self.date_time}"


class PatientFile(models.Model):
    FILE_TYPES = [
        ('rontgen', 'Röntgen'),
        ('rapor', 'Rapor'),
        ('recete', 'Reçete'),
        ('diger', 'Diğer'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='patients/files/', verbose_name="Dosya")
    file_type = models.CharField(max_length=20, choices=FILE_TYPES, default='diger')
    description = models.CharField(max_length=255, blank=True, verbose_name="Açıklama")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Hasta Dosyası"
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.patient.name} - {self.get_file_type_display()}"


class PatientToothModel(models.Model):
    FILE_FORMATS = [
        ('stl', 'STL'),
        ('obj', 'OBJ'),
        ('glb', 'GLB/GLTF'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='tooth_models')
    file = models.FileField(upload_to='patients/tooth_models/', verbose_name="3D Model Dosyası")
    file_format = models.CharField(max_length=10, choices=FILE_FORMATS, verbose_name="Format")
    description = models.CharField(max_length=255, blank=True, verbose_name="Açıklama")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Hasta Diş Modeli"
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.patient.name} - {self.file_format.upper()} Modeli"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('bekliyor',        '⏳ Bekliyor'),
        ('onaylandi',       '✅ Onaylandı'),
        ('tamamlandi',      '✔️ Tamamlandı'),
        ('tamamlanamadi',   '❌ Tamamlanamadı'),
        ('iptal',           '🚫 İptal'),
    ]
    PROCEDURE_CHOICES = [
        ('muayene',     'Muayene'),
        ('dolgu',       'Dolgu'),
        ('cekim',       'Çekim'),
        ('kanal',       'Kanal Tedavisi'),
        ('implant',     'İmplant'),
        ('kron',        'Kron/Köprü'),
        ('temizlik',    'Diş Temizliği'),
        ('beyazlatma',  'Beyazlatma'),
        ('ortodonti',   'Ortodonti'),
        ('protez',      'Protez'),
        ('rontgen',     'Röntgen'),
        ('diger',       'Diğer'),
    ]

    clinic = models.ForeignKey(
        'tenants.Clinic',
        on_delete=models.CASCADE,
        related_name='appointments',
        verbose_name="Klinik",
        null=True,
        blank=True,
    )
    patient  = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments', verbose_name='Hasta')
    doctor   = models.ForeignKey('doctors.Doctor', on_delete=models.SET_NULL, null=True, blank=True, related_name='appointments', verbose_name='Doktor')
    date_time = models.DateTimeField(verbose_name='Tarih ve Saat')
    duration  = models.PositiveIntegerField(default=30, verbose_name='Süre (dk)')
    procedure = models.CharField(max_length=50, choices=PROCEDURE_CHOICES, default='muayene', verbose_name='İşlem')
    notes     = models.TextField(blank=True, verbose_name='Notlar')
    fee       = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Ücret')
    status    = models.CharField(max_length=20, choices=STATUS_CHOICES, default='bekliyor', verbose_name='Durum')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date_time']
        verbose_name = 'Randevu'

    def __str__(self):
        return f"{self.patient.name} — {self.date_time:%d.%m.%Y %H:%M}"


# ─────────────────────────────────────────────
# BİLDİRİM MODELİ
# ─────────────────────────────────────────────

class Notification(models.Model):
    TYPE_CHOICES = [
        ('yeni_randevu', 'Yeni Randevu'),
        ('iptal_randevu', 'Randevu İptali'),
    ]

    clinic     = models.ForeignKey('tenants.Clinic', on_delete=models.CASCADE, related_name='notifications')
    type       = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title      = models.CharField(max_length=200)
    body       = models.TextField()
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Bildirim'

    def __str__(self):
        return f"{self.clinic} — {self.title}"



class HastaUser(models.Model):
    """Hasta portalı kullanıcısı — e-posta + şifre ile kimlik doğrulama"""
    BLOOD_TYPES = [
        ('A+','A Rh+'),('A-','A Rh-'),('B+','B Rh+'),('B-','B Rh-'),
        ('AB+','AB Rh+'),('AB-','AB Rh-'),('0+','0 Rh+'),('0-','0 Rh-'),
        ('bilinmiyor','Bilinmiyor'),
    ]
    first_name         = models.CharField(max_length=100, verbose_name="Ad")
    last_name          = models.CharField(max_length=100, verbose_name="Soyad")
    phone_number       = models.CharField(max_length=20, unique=True, verbose_name="Telefon")
    email              = models.EmailField(unique=True, verbose_name="E-posta")
    password           = models.CharField(max_length=255, verbose_name="Şifre")
    blood_type         = models.CharField(max_length=20, blank=True, default='', verbose_name="Kan Grubu")
    insurance_company  = models.CharField(max_length=100, blank=True, default='', verbose_name="Sigorta Şirketi")
    insurance_number   = models.CharField(max_length=50, blank=True, default='', verbose_name="Sigorta No")
    is_active          = models.BooleanField(default=True)
    created_at         = models.DateTimeField(auto_now_add=True)
    last_login         = models.DateTimeField(null=True, blank=True)
 
    class Meta:
        verbose_name = 'Hasta Kullanıcı'
 
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
 
    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"
 
    def set_password(self, raw_password):
        self.password = make_password(raw_password)
 
    def check_password(self, raw_password):
        return check_password(raw_password, self.password)
 

 
class HastaSession(models.Model):
    """Hasta oturum token'ı"""
    hasta_user = models.ForeignKey(HastaUser, on_delete=models.CASCADE, related_name='sessions')
    token      = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
 
    def is_valid(self):
        return timezone.now() < self.expires_at
 
    @classmethod
    def create_for(cls, hasta_user):
        token = secrets.token_urlsafe(48)
        return cls.objects.create(
            hasta_user=hasta_user,
            token=token,
            expires_at=timezone.now() + timedelta(days=30),
        )

# class HastaOTP(models.Model):
#     """Telefon doğrulama kodu"""
#     phone_number = models.CharField(max_length=20)
#     code         = models.CharField(max_length=6)
#     is_used      = models.BooleanField(default=False)
#     created_at   = models.DateTimeField(auto_now_add=True)
#     expires_at   = models.DateTimeField()

#     class Meta:
#         verbose_name = 'Hasta OTP'

#     def is_valid(self):
#         return not self.is_used and timezone.now() < self.expires_at

#     @classmethod
#     def create_for(cls, phone_number):
#         cls.objects.filter(phone_number=phone_number, is_used=False).update(is_used=True)
#         code = ''.join(random.choices(string.digits, k=6))
#         return cls.objects.create(
#             phone_number=phone_number,
#             code=code,
#             expires_at=timezone.now() + timedelta(minutes=10),
#         )


class HastaSession(models.Model):
    """Hasta oturum token'ı"""
    hasta_user  = models.ForeignKey(HastaUser, on_delete=models.CASCADE, related_name='sessions')
    token       = models.CharField(max_length=64, unique=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    expires_at  = models.DateTimeField()

    def is_valid(self):
        return timezone.now() < self.expires_at

    @classmethod
    def create_for(cls, hasta_user):
        import secrets
        token = secrets.token_urlsafe(48)
        return cls.objects.create(
            hasta_user=hasta_user,
            token=token,
            expires_at=timezone.now() + timedelta(days=30),
        )