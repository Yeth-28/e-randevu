from django.urls import set_urlconf
from django.conf import settings
from django.http import HttpResponseForbidden


class PanelSubdomainMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Port numarasını ve boşlukları temizle
        host = request.get_host().split(':')[0].lower().strip()

        # Settings'deki alan adları
        base_domain  = getattr(settings, 'BASE_DOMAIN',  'e-randevu.online')
        panel_domain = getattr(settings, 'PANEL_DOMAIN', f'panel.{base_domain}')
        hasta_domain = getattr(settings, 'HASTA_DOMAIN', f'hasta.{base_domain}')

        # 1. Ortak Yönetim Paneli (panel.e-randevu.online VEYA panel.localhost)
        if host in (panel_domain, 'panel.localhost'):
            if request.path.startswith('/doktor/'):
                request.urlconf = 'dental.doktor_urls'
                set_urlconf('dental.doktor_urls')
            else:
                request.urlconf = 'dental.panel_urls'
                set_urlconf('dental.panel_urls')

        # 2. Ana Hasta Sitesi (e-randevu.online, hasta.e-randevu.online, hasta.localhost, localhost)
        elif host in (base_domain, hasta_domain, 'hasta.localhost', 'localhost', '127.0.0.1'):
            if not request.path.startswith('/superadmin/') and \
               not request.path.startswith('/admin/'):
                request.urlconf = 'dental.hasta_ana_urls'
                set_urlconf('dental.hasta_ana_urls')
            else:
                set_urlconf(None)

        # 3. Özel Klinik Subdomain'leri (örn: ahmet-klinik.e-randevu.online)
        elif (
            host.endswith(f'.{base_domain}') or
            host.endswith(f'.{hasta_domain}') or
            host.endswith('.localhost')
        ) and host not in (panel_domain, hasta_domain, 'panel.localhost', 'hasta.localhost'):
            request.urlconf = 'dental.hasta_klinik_urls'
            set_urlconf('dental.hasta_klinik_urls')

        else:
            set_urlconf(None)

        response = self.get_response(request)
        set_urlconf(None)
        return response


class SuperAdminIPMiddleware:
    ALLOWED_IPS = {'127.0.0.1', '::1', 'localhost'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/superadmin/'):
            ip = self._get_ip(request)
            if ip not in self.ALLOWED_IPS:
                return HttpResponseForbidden(
                    '<h1>403 Erişim Engellendi</h1>'
                    '<p>Süper admin paneline sadece sunucu içinden erişilebilir.</p>'
                )
        return self.get_response(request)

    def _get_ip(self, request):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')