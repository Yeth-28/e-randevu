from django.urls import path
from tenants.hasta_views import klinik_randevu_sayfasi, randevu_basarili

urlpatterns = [
    path('',          klinik_randevu_sayfasi),
    path('basarili/', randevu_basarili),
]

from django.conf import settings
from django.conf.urls.static import static
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)