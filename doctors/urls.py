from django.urls import path
from tenants.views import panel_giris, panel_dashboard
from doctors.views import doktor_listesi, doktor_ekle, doktor_duzenle, doktor_sil

urlpatterns = [
    path('giris/', panel_giris, name='panel_giris'),
    path('<str:clinic_id>/', panel_dashboard, name='panel_dashboard'),
    path('<str:clinic_id>/doktorlar/', doktor_listesi, name='doktor_listesi'),
    path('<str:clinic_id>/doktorlar/ekle/', doktor_ekle, name='doktor_ekle'),
    path('<str:clinic_id>/doktorlar/<int:doktor_id>/duzenle/', doktor_duzenle, name='doktor_duzenle'),
    path('<str:clinic_id>/doktorlar/<int:doktor_id>/sil/', doktor_sil, name='doktor_sil'),
]