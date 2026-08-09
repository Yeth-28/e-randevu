import random
import string
from django.db import migrations, models


def generate_codes(apps, schema_editor):
    Doctor = apps.get_model('doctors', 'Doctor')
    used = set()
    for doctor in Doctor.objects.filter(login_code=''):
        while True:
            code = ''.join(random.choices(string.digits, k=6))
            if code not in used and not Doctor.objects.filter(login_code=code).exists():
                used.add(code)
                break
        doctor.login_code = code
        doctor.save(update_fields=['login_code'])


class Migration(migrations.Migration):

    dependencies = [
        ('doctors', '0004_doctorlogincode_doctorsession'),
    ]

    operations = [
        # 1. Önce unique olmadan, boş string default ile ekle
        migrations.AddField(
            model_name='doctor',
            name='login_code',
            field=models.CharField(blank=True, default='', max_length=6, verbose_name='Giriş Kodu'),
        ),
        # 2. Mevcut kayıtlara benzersiz kod ata
        migrations.RunPython(generate_codes, migrations.RunPython.noop),
        # 3. Şimdi unique constraint ekle
        migrations.AlterField(
            model_name='doctor',
            name='login_code',
            field=models.CharField(
                blank=True, max_length=6, unique=True,
                verbose_name='Giriş Kodu',
                help_text='Doktorun panele giriş için kullandığı 6 haneli kod'
            ),
        ),
    ]