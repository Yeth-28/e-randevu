@echo off
REM ─────────────────────────────────────────────────────────────────
REM DentalReserv — Waitress Server Başlatma
REM Bu dosyayı NSSM servisi olarak veya elle çalıştır
REM ─────────────────────────────────────────────────────────────────

cd /d C:\dental_management_system

REM .env dosyasını yükle
set DJANGO_SETTINGS_MODULE=dental.settings

echo [DentalReserv] Sunucu başlatılıyor...
echo [DentalReserv] http://127.0.0.1:8000

venv\Scripts\waitress-serve.exe ^
    --host=127.0.0.1 ^
    --port=8000 ^
    --threads=8 ^
    --connection-limit=1000 ^
    --channel-timeout=120 ^
    dental.wsgi:application