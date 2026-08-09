from django.urls import path
from . import views

urlpatterns = [
    path('', views.klinik_kayit, name='klinik_kayit'),
]