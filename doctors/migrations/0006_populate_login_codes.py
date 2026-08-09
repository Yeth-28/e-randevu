import random
import string
from django.db import migrations


def populate_codes(apps, schema_editor):
    Doctor = apps.get_model('doctors', 'Doctor')
    used   = set(Doctor.objects.exclude(login_code='').values_list('login_code', flat=True))

    for doctor in Doctor.objects.filter(login_code=''):
        while True:
            code = ''.join(random.choices(string.digits, k=6))
            if code not in used:
                used.add(code)
                break
        doctor.login_code = code
        doctor.save(update_fields=['login_code'])


class Migration(migrations.Migration):

    dependencies = [
        ('doctors', '0005_doctor_login_code'),
    ]

    operations = [
        migrations.RunPython(populate_codes, migrations.RunPython.noop),
    ]