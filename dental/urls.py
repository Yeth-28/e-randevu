"""
Root URLConf (dental.urls)

Bu dosya SADECE şu durumlarda devrededir:
  - /admin/ ve /superadmin/ yolları (host'tan bağımsız, middleware tarafından
    özellikle bu urlconf'a bırakılır)
  - Middleware'in hiçbir branch'inde eşleşmeyen host'lar (örn. doğrudan
    *.onrender.com üzerinden erişim, yanlış yapılandırılmış bir domain)

panel.e-randevu.online, e-randevu.online, hasta.e-randevu.online ve
<klinik>.e-randevu.online için gerçek routing dental/middleware.py içindeki
PanelSubdomainMiddleware tarafından yapılır (bkz. panel_urls.py,
hasta_ana_urls.py, hasta_klinik_urls.py, doktor_urls.py).
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from tenants.views import (
    superadmin_giris, superadmin_dashboard,
    superadmin_klinik_detay, superadmin_klinik_duzenle,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    path('kayit/',   include('tenants.urls')),
    path('clinics/', include('clinics.urls')),
    path('doctors/', include('doctors.urls')),
    path('patients/', include('patients.urls')),
    path('accounts/', include('django.contrib.auth.urls')),

    path('api/clinics/',  include('clinics.api_urls')),
    path('api/doctors/',  include('doctors.api_urls')),
    path('api/patients/', include('patients.api_urls')),

    path('superadmin/giris/', superadmin_giris, name='superadmin_giris'),
    path('superadmin/', superadmin_dashboard, name='superadmin_dashboard'),
    path('superadmin/klinik/<str:clinic_id>/', superadmin_klinik_detay, name='superadmin_klinik_detay'),
    path('superadmin/klinik/<str:clinic_id>/duzenle/', superadmin_klinik_duzenle, name='superadmin_klinik_duzenle'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
