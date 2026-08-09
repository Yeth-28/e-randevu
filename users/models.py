from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True)
    
    ROLE_CHOICES = [
        ('clinic_owner', '👑 Klinik Sahibi'),
        ('doctor',       '👨‍⚕️ Doktor'),
        ('patient',      '🧑‍🦷 Hasta'),
    ]
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='patient',
        verbose_name="Rol"
    )
    phone = models.CharField(max_length=15, blank=True, verbose_name="Telefon")
    avatar = models.ImageField(
        upload_to='avatars/', 
        blank=True, 
        null=True,
        verbose_name="Profil Fotoğrafı"
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    @property
    def is_clinic_owner(self):
        return self.role == 'clinic_owner'

    @property
    def is_doctor(self):
        return self.role == 'doctor'

    @property
    def is_patient(self):
        return self.role == 'patient'

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"