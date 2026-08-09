from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from doctors.doktor_views import (
    doktor_giris, doktor_kod, doktor_cikis,
    doktor_dashboard, doktor_randevular,
    doktor_hastalar, doktor_hasta_detay,
    doktor_ziyaret_duzenle,
    doktor_bildirim_listesi, doktor_bildirim_okundu,
    doktor_bildirimler,
    doktor_snapshot_ekle, doktor_snapshot_sil,
)

urlpatterns = [
    path('doktor/giris/', doktor_giris, name='doktor_giris'),
    path('doktor/kod/',   doktor_kod,   name='doktor_kod'),
    path('doktor/cikis/', doktor_cikis, name='doktor_cikis'),

    path('doktor/<str:clinic_id>/dashboard/',   doktor_dashboard,  name='doktor_dashboard'),
    path('doktor/<str:clinic_id>/randevular/',  doktor_randevular, name='doktor_randevular'),
    path('doktor/<str:clinic_id>/hastalar/',    doktor_hastalar,   name='doktor_hastalar'),

    path('doktor/<str:clinic_id>/hastalar/<int:hasta_id>/',                  doktor_hasta_detay, name='doktor_hasta_detay'),
    path('doktor/<str:clinic_id>/hastalar/<int:hasta_id>/dosya/yukle/',      doktor_hasta_detay, name='doktor_hasta_dosya_yukle'),
    path('doktor/<str:clinic_id>/hastalar/<int:hasta_id>/ziyaret/ekle/',     doktor_hasta_detay, name='doktor_ziyaret_ekle'),
    path('doktor/<str:clinic_id>/hastalar/<int:hasta_id>/ziyaret/<int:ziyaret_id>/duzenle/', doktor_ziyaret_duzenle, name='doktor_ziyaret_duzenle'),
    path('doktor/<str:clinic_id>/hastalar/<int:hasta_id>/snapshot/ekle/',    doktor_snapshot_ekle, name='doktor_snapshot_ekle'),
    path('doktor/<str:clinic_id>/hastalar/<int:hasta_id>/snapshot/<int:snapshot_id>/sil/', doktor_snapshot_sil, name='doktor_snapshot_sil'),

    path('doktor/<str:clinic_id>/bildirimler/',            doktor_bildirimler,      name='doktor_bildirimler'),
    path('doktor/<str:clinic_id>/api/bildirimler/',         doktor_bildirim_listesi, name='doktor_bildirim_listesi'),
    path('doktor/<str:clinic_id>/api/bildirimler/okundu/',  doktor_bildirim_okundu,  name='doktor_bildirim_okundu'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
