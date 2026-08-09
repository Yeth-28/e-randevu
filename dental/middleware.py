from django.urls import set_urlconf
from django.conf import settings
from django.http import HttpResponseForbidden


def _normalize_host(request):
    """Host header'ı port, sondaki nokta ve baştaki 'www.' önekinden arındırır."""
    host = request.get_host().split(':')[0].lower().strip()
    host = host.rstrip('.')
    if host.startswith('www.'):
        host = host[4:]
    return host


class PanelSubdomainMiddleware:
    """
    Host header'ına göre hangi URLConf'un kullanılacağına karar verir.

    ÖNEMLİ (kök neden notu): Bu middleware'in doğru çalışması tamamen
    settings.py'deki BASE_DOMAIN / PANEL_DOMAIN / HASTA_DOMAIN değerlerinin
    production'da doğru resolve edilmesine bağlıdır. DEBUG yanlışlıkla True
    kalırsa PANEL_DOMAIN 'panel.localhost' olur ve gerçek istek host'u
    'panel.e-randevu.online' hiçbir exact-match'e girmeden 3. branch'e
    (klinik subdomain) düşer. Bu yüzden settings.py'de DEBUG default=False
    yapıldı ve Render'da DEBUG env-var'ının kesinlikle set edilmemiş/False
    olması gerekiyor.

    Öncelik sırası kasıtlıdır ve DEĞİŞTİRİLMEMELİDİR:
      1) Panel (tam eşleşme)      -> en spesifik, önce kontrol edilmeli
      2) Ana hasta / apex domain  -> tam eşleşme
      3) Klinik subdomain (wildcard) -> en genel, en sonda kontrol edilmeli
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = _normalize_host(request)

        base_domain  = getattr(settings, 'BASE_DOMAIN',  'e-randevu.online').lower()
        panel_domain = getattr(settings, 'PANEL_DOMAIN', f'panel.{base_domain}').lower()
        hasta_domain = getattr(settings, 'HASTA_DOMAIN', f'hasta.{base_domain}').lower()

        is_superadmin_path = request.path.startswith('/superadmin/') or request.path.startswith('/admin/')

        # 1) Ortak Klinik Yönetim Paneli — panel.e-randevu.online / panel.localhost
        if host in (panel_domain, 'panel.localhost'):
            if request.path.startswith('/doktor/'):
                request.urlconf = 'dental.doktor_urls'
            else:
                request.urlconf = 'dental.panel_urls'
            set_urlconf(request.urlconf)

        # 2) Ana Hasta Portalı — e-randevu.online (apex), hasta.e-randevu.online, hasta.localhost, localhost
        elif host in (base_domain, hasta_domain, 'hasta.localhost', 'localhost', '127.0.0.1'):
            if is_superadmin_path:
                # /admin/ ve /superadmin/ her zaman root URLConf (dental.urls) üzerinden gider
                request.urlconf = None
                set_urlconf(None)
            else:
                request.urlconf = 'dental.hasta_ana_urls'
                set_urlconf(request.urlconf)

        # 3) Özel Klinik Subdomain'leri — ahmet-dis.e-randevu.online, kliniklar.localhost vb.
        #    (panel/hasta exact-match'lerinden SONRA kontrol edilir, aksi halde
        #     panel.* veya hasta.* burada yakalanıp "klinik bulunamadı" hatası verir.)
        elif (
            host.endswith(f'.{base_domain}') or host.endswith('.localhost')
        ) and host not in (panel_domain, hasta_domain, 'panel.localhost', 'hasta.localhost'):
            request.urlconf = 'dental.hasta_klinik_urls'
            set_urlconf(request.urlconf)

        # 4) Eşleşmeyen host (örn. *.onrender.com ile doğrudan erişim, admin IP'den erişim)
        #    -> varsayılan ROOT_URLCONF (dental.urls) devrede kalır.
        else:
            request.urlconf = None
            set_urlconf(None)

        response = self.get_response(request)
        set_urlconf(None)
        return response


class SuperAdminIPMiddleware:
    """
    /superadmin/ yalnızca sunucunun kendisinden (localhost) veya
    SUPERADMIN_ALLOWED_IPS env-var'ında tanımlı IP'lerden erişilebilir olsun diye.
    Render gibi platformlarda uygulama bir proxy arkasında çalıştığından
    X-Forwarded-For header'ı dikkate alınır.
    """
    ALLOWED_IPS = {'127.0.0.1', '::1'}

    def __init__(self, get_response):
        self.get_response = get_response
        extra = getattr(settings, 'SUPERADMIN_ALLOWED_IPS', [])
        if extra:
            self.ALLOWED_IPS = self.ALLOWED_IPS | set(extra)

    def __call__(self, request):
        if request.path.startswith('/superadmin/'):
            ip = self._get_ip(request)
            if ip not in self.ALLOWED_IPS:
                return HttpResponseForbidden(
                    '<h1>403 Erişim Engellendi</h1>'
                    '<p>Süper admin paneline sadece yetkili IP adreslerinden erişilebilir.</p>'
                )
        return self.get_response(request)

    def _get_ip(self, request):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
