import os
from pathlib import Path
from decouple import config, Csv
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# ─── TEMEL ────────────────────────────────────────────────────────────────────
SECRET_KEY = config('SECRET_KEY', default='django-insecure-secret-key-change-in-prod')
DEBUG       = config('DEBUG', default=True, cast=bool)

# ─── DOMAIN AYARLARI ──────────────────────────────────────────────────────────
# Canlı ortamda (Render) butonların localhost'a yönlenmesini engellemek için doğrudan tanımlandı:
BASE_DOMAIN  = config('BASE_DOMAIN',  default='e-randevu.online')

if DEBUG:
    PANEL_DOMAIN = config('PANEL_DOMAIN', default='panel.localhost')
    HASTA_DOMAIN = config('HASTA_DOMAIN', default='hasta.localhost')
    SITE_URL     = config('SITE_URL',     default='http://hasta.localhost:8000')
    PANEL_URL    = config('PANEL_URL',    default='http://panel.localhost:8000')
else:
    PANEL_DOMAIN = config('PANEL_DOMAIN', default=f'panel.{BASE_DOMAIN}')
    HASTA_DOMAIN = config('HASTA_DOMAIN', default=f'hasta.{BASE_DOMAIN}')
    SITE_URL     = config('SITE_URL',     default=f'https://{BASE_DOMAIN}')
    PANEL_URL    = config('PANEL_URL',    default=f'https://panel.{BASE_DOMAIN}')

ALLOWED_HOSTS = ['*'] if DEBUG else [
    BASE_DOMAIN,
    f'.{BASE_DOMAIN}',
    PANEL_DOMAIN,
    HASTA_DOMAIN,
    'localhost',
    '127.0.0.1',
    '.onrender.com',
]

# ─── MULTI-TENANT APPS ────────────────────────────────────────────────────────
SHARED_APPS = [
    'django_tenants',
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'crispy_forms',
    'crispy_bootstrap5',
    'tenants',
    'users',
    'doctors',
    'patients',
]

TENANT_APPS = [
    'clinics',
    'doctors',
    'patients',
]

INSTALLED_APPS = list(SHARED_APPS) + [
    app for app in TENANT_APPS if app not in SHARED_APPS
]

TENANT_MODEL        = "tenants.Clinic"
TENANT_DOMAIN_MODEL = "tenants.Domain"

# ─── MIDDLEWARE ───────────────────────────────────────────────────────────────
MIDDLEWARE = [
    #'django_tenants.middleware.main.TenantMainMiddleware',
    'dental.middleware.PanelSubdomainMiddleware',
    'dental.middleware.SuperAdminIPMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Statik dosyalar (CSS/JS) için
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'dental.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'dental.context_processors.site_urls',
            ],
        },
    },
]

WSGI_APPLICATION = 'dental.wsgi.application'

# ─── VERİTABANI (Render + Neon Postgres / Local Uyumlu) ─────────────────────────
DATABASE_URL = config('DATABASE_URL', default=None)

if DATABASE_URL:
    # Render / Production Ortamı (DATABASE_URL Varsa)
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=True
        )
    }
    DATABASES['default']['ENGINE'] = 'django_tenants.postgresql_backend'
else:
    # Lokal Geliştirme Ortamı
    DATABASES = {
        'default': {
            'ENGINE':   'django_tenants.postgresql_backend',
            'NAME':     config('DB_NAME',     default='e-randevu'),
            'USER':     config('DB_USER',     default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST':     config('DB_HOST',     default='localhost'),
            'PORT':     config('DB_PORT',     default='5432'),
        }
    }

DATABASE_ROUTERS = ('django_tenants.routers.TenantSyncRouter',)

# ─── AUTH ─────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL     = 'users.User'
LOGIN_REDIRECT_URL  = 'home'
LOGOUT_REDIRECT_URL = 'login'

ROLE_CLINIC_OWNER = 'clinic_owner'
ROLE_DOCTOR       = 'doctor'
ROLE_PATIENT      = 'patient'

# ─── CRISPY FORMS ─────────────────────────────────────────────────────────────
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK          = "bootstrap5"

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── DİL & ZAMAN ──────────────────────────────────────────────────────────────
LANGUAGE_CODE = 'tr-tr'
TIME_ZONE     = 'Europe/Istanbul'
USE_I18N      = True
USE_TZ        = True

# ─── STATİK & MEDIA ───────────────────────────────────────────────────────────
STATIC_URL       = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT      = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_URL        = '/media/'
MEDIA_ROOT       = os.path.join(BASE_DIR, 'media')

# WhiteNoise Statik Dosya Sıkıştırma
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── iyzico ───────────────────────────────────────────────────────────────────
IYZICO_API_KEY    = config('IYZICO_API_KEY',    default='sandbox-api-key')
IYZICO_SECRET_KEY = config('IYZICO_SECRET_KEY', default='sandbox-secret-key')
IYZICO_BASE_URL   = config('IYZICO_BASE_URL',   default='https://sandbox-api.iyzipay.com')

# ─── E-POSTA ──────────────────────────────────────────────────────────────────
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = config('EMAIL_HOST',          default='smtp.gmail.com')
EMAIL_PORT          = config('EMAIL_PORT',          default=587, cast=int)
EMAIL_USE_TLS       = config('EMAIL_USE_TLS',       default=True, cast=bool)
EMAIL_HOST_USER     = config('EMAIL_HOST_USER',     default='talhameteacar01@gmail.com')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='ydao pzpg xbmo bqby')
DEFAULT_FROM_EMAIL  = config('EMAIL_HOST_USER',     default='noreply@e-randevu.online')

# ─── CSRF & SESSION ───────────────────────────────────────────────────────────
CSRF_TRUSTED_ORIGINS = [
    f'http://{PANEL_DOMAIN}', f'https://{PANEL_DOMAIN}',
    f'http://{HASTA_DOMAIN}', f'https://{HASTA_DOMAIN}',
    f'https://*.{BASE_DOMAIN}',
    f'https://{BASE_DOMAIN}',
    'https://*.onrender.com',
    'http://panel.localhost:8000',
    'http://hasta.localhost:8000',
    'http://*.hasta.localhost:8000',
]

SESSION_COOKIE_DOMAIN = None
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_ENGINE        = 'django.contrib.sessions.backends.db'

# ─── PRODUCTION GÜVENLİK (DEBUG=False olunca otomatik aktif) ─────────────────
if not DEBUG:
    SECURE_SSL_REDIRECT             = True
    SESSION_COOKIE_SECURE           = True
    CSRF_COOKIE_SECURE              = True
    SECURE_BROWSER_XSS_FILTER       = True
    SECURE_CONTENT_TYPE_NOSNIFF     = True
    SECURE_HSTS_SECONDS             = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS  = True
    X_FRAME_OPTIONS                 = 'DENY'