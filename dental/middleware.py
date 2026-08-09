from django.urls import set_urlconf
from django.conf import settings
from django.http import HttpResponseForbidden


class PanelSubdomainMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host         = request.get_host().split(':')[0].lower().strip()
        panel_domain = getattr(settings, 'PANEL_DOMAIN', 'panel.localhost')
        hasta_domain = getattr(settings, 'HASTA_DOMAIN', 'hasta.localhost')
        base_domain  = getattr(settings, 'BASE_DOMAIN',  'e-randevu.online')

        if host == panel_domain:
            # Klinik yönetim paneli
            if request.path.startswith('/doktor/'):
                request.urlconf = 'dental.doktor_urls'
                set_urlconf('dental.doktor_urls')
            else:
                request.urlconf = 'dental.panel_urls'
                set_urlconf('dental.panel_urls')

        elif host in (hasta_domain, base_domain, 'localhost'):
            # Ana hasta sitesi — localhost:8000 veya e-randevu.online
            # Superadmin ve diğer özel path'ler hariç
            if not request.path.startswith('/superadmin/') and \
               not request.path.startswith('/admin/'):
                request.urlconf = 'dental.hasta_ana_urls'
                set_urlconf('dental.hasta_ana_urls')
            else:
                set_urlconf(None)

        elif (
            host.endswith(f'.{base_domain}') or
            host.endswith(f'.{hasta_domain}') or
            (host.endswith('.localhost') and host not in (panel_domain,))
        ):
            # Klinik subdomain — aliklinik.e-randevu.online veya aliklinik.localhost
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