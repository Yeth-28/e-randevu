from django.conf import settings


def site_urls(request):
    """
    Tüm template'lere otomatik inject edilir.
    Kullanım: {{ PANEL_URL }}/{{ clinic_id }}/hastalar/
    """
    return {
        'PANEL_URL':  getattr(settings, 'PANEL_URL',  'http://panel.localhost:8000'),
        'SITE_URL':   getattr(settings, 'SITE_URL',   'http://hasta.localhost:8000'),
        'PANEL_DOMAIN': getattr(settings, 'PANEL_DOMAIN', 'panel.localhost'),
        'HASTA_DOMAIN': getattr(settings, 'HASTA_DOMAIN', 'hasta.localhost'),
        'BASE_DOMAIN':  getattr(settings, 'BASE_DOMAIN',  'e-randevu.online'),
    }