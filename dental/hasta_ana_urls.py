from django.urls import path
from tenants.hasta_views import (
    ana_sayfa, klinik_ara_api,
    hasta_giris, hasta_kayit, hasta_cikis,
    hasta_profili, randevu_iptal,
)

urlpatterns = [
    path('',                                              ana_sayfa),
    path('api/klinik-ara/',                               klinik_ara_api),
    path('hasta/giris/',                                  hasta_giris),
    path('hasta/kayit/',                                  hasta_kayit),
    path('hasta/cikis/',                                  hasta_cikis),
    path('hasta/profilim/',                               hasta_profili),
    path('hasta/randevu/<int:randevu_id>/iptal/',         randevu_iptal),
]

from django.conf import settings
from django.conf.urls.static import static
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)