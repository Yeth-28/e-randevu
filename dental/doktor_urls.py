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
    path('doktor/giris/',                                                                       doktor_giris),
    path('doktor/kod/',                                                                         doktor_kod),
    path('doktor/cikis/',                                                                       doktor_cikis),
    path('doktor/<str:clinic_id>/dashboard/',                                                   doktor_dashboard),
    path('doktor/<str:clinic_id>/randevular/',                                                  doktor_randevular),
    path('doktor/<str:clinic_id>/hastalar/',                                                    doktor_hastalar),
    path('doktor/<str:clinic_id>/hastalar/<int:hasta_id>/',                                     doktor_hasta_detay),
    path('doktor/<str:clinic_id>/hastalar/<int:hasta_id>/dosya/yukle/',                         doktor_hasta_detay),
    path('doktor/<str:clinic_id>/hastalar/<int:hasta_id>/ziyaret/ekle/',                        doktor_hasta_detay),
    path('doktor/<str:clinic_id>/hastalar/<int:hasta_id>/ziyaret/<int:ziyaret_id>/duzenle/',    doktor_ziyaret_duzenle),
    path('doktor/<str:clinic_id>/hastalar/<int:hasta_id>/snapshot/ekle/',                        doktor_snapshot_ekle),
    path('doktor/<str:clinic_id>/hastalar/<int:hasta_id>/snapshot/<int:snapshot_id>/sil/',      doktor_snapshot_sil),
    path('doktor/<str:clinic_id>/bildirimler/',                                                doktor_bildirimler),
    path('doktor/<str:clinic_id>/api/bildirimler/',                                             doktor_bildirim_listesi),
    path('doktor/<str:clinic_id>/api/bildirimler/okundu/',                                      doktor_bildirim_okundu),
]

from django.conf import settings
from django.conf.urls.static import static
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)