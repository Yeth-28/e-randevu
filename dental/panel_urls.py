from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from patients.views import (
    hasta_listesi, hasta_ekle, hasta_detay, hasta_duzenle, hasta_sil,
    ziyaret_ekle, ziyaret_duzenle,
    dis_haritasi_guncelle, dosya_yukle, tooth_model_yukle,
    randevu_listesi, randevu_ekle, randevu_guncelle, randevu_sil,
    bildirim_listesi, bildirim_okundu, bildirim_merkezi,
    raporlama, snapshot_ekle, snapshot_sil,
)
from doctors.views import (
    doktor_listesi, doktor_ekle, doktor_duzenle, doktor_sil,
)
from tenants.views import panel_giris, panel_dashboard, klinik_kayit
from tenants.odeme_views import abonelik_planlar, abonelik_odeme, abonelik_basarili
from dental.ayarlar_dogrulama_views import ayarlar_kod_gonder, ayarlar_dogrula_api
from patients.ayarlar_views import (
    ayarlar, ayarlar_klinik_bilgileri, ayarlar_calisma_saatleri,
    ayarlar_tatil_ekle, ayarlar_tatil_sil, ayarlar_randevu,
    ayarlar_bildirim, ayarlar_doktor_saatleri,
    ayarlar_kart_guncelle, ayarlar_kart_aktif, ayarlar_kart_sil,
    ayarlar_kart_duzenle, ayarlar_kart_aktif_sec,
)

# NOT: Bu dosya panel.e-randevu.online host'u için dental.middleware.PanelSubdomainMiddleware
# tarafından request.urlconf olarak set edilir. Sabit yollar (kayit/, giris/) MUTLAKA
# <str:clinic_id>/ catch-all'ından ÖNCE tanımlanmalı, aksi halde clinic_id="kayit" gibi
# yanlış eşleşmeler oluşur. Dashboard catch-all EN SONDA kalmalı.

urlpatterns = [
    path('kayit/', klinik_kayit, name='panel_klinik_kayit'),
    path('giris/', panel_giris, name='panel_giris'),

    # Doktorlar
    path('<str:clinic_id>/doktorlar/',                              doktor_listesi, name='doktor_listesi'),
    path('<str:clinic_id>/doktorlar/ekle/',                         doktor_ekle,    name='doktor_ekle'),
    path('<str:clinic_id>/doktorlar/<int:doktor_id>/duzenle/',      doktor_duzenle, name='doktor_duzenle'),
    path('<str:clinic_id>/doktorlar/<int:doktor_id>/sil/',          doktor_sil,     name='doktor_sil'),

    # Hastalar
    path('<str:clinic_id>/hastalar/',                               hasta_listesi,  name='panel_hasta_listesi'),
    path('<str:clinic_id>/hastalar/ekle/',                          hasta_ekle,     name='panel_hasta_ekle'),
    path('<str:clinic_id>/hastalar/<int:hasta_id>/',                hasta_detay,    name='panel_hasta_detay'),
    path('<str:clinic_id>/hastalar/<int:hasta_id>/duzenle/',        hasta_duzenle,  name='panel_hasta_duzenle'),
    path('<str:clinic_id>/hastalar/<int:hasta_id>/sil/',            hasta_sil,      name='panel_hasta_sil'),

    # Ziyaretler
    path('<str:clinic_id>/hastalar/<int:hasta_id>/ziyaret/ekle/',                     ziyaret_ekle,    name='ziyaret_ekle'),
    path('<str:clinic_id>/hastalar/<int:hasta_id>/ziyaret/<int:ziyaret_id>/duzenle/', ziyaret_duzenle, name='ziyaret_duzenle'),

    # Diş haritası & dosyalar
    path('<str:clinic_id>/hastalar/<int:hasta_id>/dis-haritasi/',      dis_haritasi_guncelle, name='dis_haritasi_guncelle'),
    path('<str:clinic_id>/hastalar/<int:hasta_id>/dosya/yukle/',       dosya_yukle,           name='dosya_yukle'),
    path('<str:clinic_id>/hastalar/<int:hasta_id>/tooth-model/yukle/', tooth_model_yukle,     name='tooth_model_yukle'),

    # Diş haritası snapshot
    path('<str:clinic_id>/hastalar/<int:hasta_id>/snapshot/ekle/',                  snapshot_ekle, name='snapshot_ekle'),
    path('<str:clinic_id>/hastalar/<int:hasta_id>/snapshot/<int:snapshot_id>/sil/', snapshot_sil,  name='snapshot_sil'),

    # Randevular
    path('<str:clinic_id>/randevular/',                             randevu_listesi,  name='panel_randevu_listesi'),
    path('<str:clinic_id>/randevular/ekle/',                        randevu_ekle,     name='panel_randevu_ekle'),
    path('<str:clinic_id>/randevular/<int:randevu_id>/guncelle/',   randevu_guncelle, name='panel_randevu_guncelle'),
    path('<str:clinic_id>/randevular/<int:randevu_id>/sil/',        randevu_sil,      name='panel_randevu_sil'),

    # Bildirimler
    path('<str:clinic_id>/api/bildirimler/',        bildirim_listesi, name='panel_bildirim_listesi'),
    path('<str:clinic_id>/api/bildirimler/okundu/', bildirim_okundu,  name='panel_bildirim_okundu'),
    path('<str:clinic_id>/bildirimler/',            bildirim_merkezi, name='panel_bildirim_merkezi'),

    # Abonelik
    path('<str:clinic_id>/abonelik/',                             abonelik_planlar,  name='abonelik_planlar'),
    path('<str:clinic_id>/abonelik/<str:plan_key>/<str:period>/', abonelik_odeme,    name='abonelik_odeme'),
    path('<str:clinic_id>/abonelik/basarili/',                    abonelik_basarili, name='abonelik_basarili'),

    # Raporlar
    path('<str:clinic_id>/raporlar/', raporlama, name='raporlama'),

    # Ayarlar
    path('<str:clinic_id>/ayarlar/',                            ayarlar,                  name='ayarlar'),
    path('<str:clinic_id>/ayarlar/klinik/',                     ayarlar_klinik_bilgileri, name='ayarlar_klinik_bilgileri'),
    path('<str:clinic_id>/ayarlar/saatler/',                    ayarlar_calisma_saatleri, name='ayarlar_calisma_saatleri'),
    path('<str:clinic_id>/ayarlar/tatil/ekle/',                 ayarlar_tatil_ekle,       name='ayarlar_tatil_ekle'),
    path('<str:clinic_id>/ayarlar/tatil/<int:tatil_id>/sil/',   ayarlar_tatil_sil,        name='ayarlar_tatil_sil'),
    path('<str:clinic_id>/ayarlar/randevu/',                    ayarlar_randevu,          name='ayarlar_randevu'),
    path('<str:clinic_id>/ayarlar/bildirim/',                   ayarlar_bildirim,         name='ayarlar_bildirim'),
    path('<str:clinic_id>/ayarlar/doktor-saatleri/',            ayarlar_doktor_saatleri,  name='ayarlar_doktor_saatleri'),
    path('<str:clinic_id>/ayarlar/kart-guncelle/',              ayarlar_kart_guncelle,    name='ayarlar_kart_guncelle'),
    path('<str:clinic_id>/ayarlar/kart/<int:kart_id>/aktif/',   ayarlar_kart_aktif,       name='ayarlar_kart_aktif'),
    path('<str:clinic_id>/ayarlar/kart/<int:kart_id>/sil/',     ayarlar_kart_sil,         name='ayarlar_kart_sil'),
    path('<str:clinic_id>/ayarlar/kart/<int:kart_id>/duzenle/', ayarlar_kart_duzenle,     name='ayarlar_kart_duzenle'),
    path('<str:clinic_id>/ayarlar/kart/aktif-sec/',             ayarlar_kart_aktif_sec,   name='ayarlar_kart_aktif_sec'),

    # Klinik Ayarları Accordion Doğrulama
    path('<str:clinic_id>/klinik-ayarlar-kod-gonder/', ayarlar_kod_gonder,   name='ayarlar_kod_gonder'),
    path('<str:clinic_id>/klinik-ayarlar-dogrula/',    ayarlar_dogrula_api, name='ayarlar_dogrula_api'),

    # Dashboard — EN SONDA OLMALI (catch-all <str:clinic_id>/)
    path('<str:clinic_id>/', panel_dashboard, name='panel_dashboard'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
