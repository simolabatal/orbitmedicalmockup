import os
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('DJANGO_SECRET_KEY', default='dev-secret-key-change-in-production')

DEBUG = config('DJANGO_DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS', default='*', cast=Csv())
ALLOWED_HOSTS = ['*']

AUTH_USER_MODEL = 'accounts.User'

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',

    # 'core' doit preceder 'staticfiles' pour que la commande runserver
    # personnalisee (auto-bridge) prenne le pas sur celle de staticfiles.
    'core',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_filters',

    'accounts',
    'iot',
    'marketplace',
    'subscriptions',
    'apps.dashboard',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'core.security_middleware.SecurityLoggingMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.security_middleware.RestrictAccessMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOW_ALL_ORIGINS = True

ROOT_URLCONF = 'lfellah_server.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR.parent / 'apps' / 'dashboard' / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'core.context_processors.roles',
            ],
        },
    },
]

WSGI_APPLICATION = 'lfellah_server.wsgi.application'

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'core' / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'


# ─── DRF ─────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}


# ─── CELERY ──────────────────────────────────────────────────────
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Casablanca'
CELERY_TASK_ALWAYS_EAGER = config('CELERY_TASK_ALWAYS_EAGER', default=False, cast=bool)


# ─── CELERY BEAT ─────────────────────────────────────────────────
# from celery.schedules import crontab

# CELERY_BEAT_SCHEDULE = {
#     'check-offline-devices': {
#         'task': 'core.tasks.check_device_offline_alerts',
#         'schedule': crontab(minute='*/15'),
#     },
# }


# ─── EMAIL ───────────────────────────────────────────────────────
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@lfellah.ma')

# ── Password Reset — securite ──────────────────────────────────
PASSWORD_RESET_TIMEOUT = 86400  # 24 heures (en secondes)


# ─── CLÉS API ────────────────────────────────────────────────────
GEMINI_API_KEY = config('GEMINI_API_KEY', default='')
OPENWEATHER_API_KEY = config('OPENWEATHER_API_KEY', default='')


# ─── JAZZMIN ─────────────────────────────────────────────────────
JAZZMIN_SETTINGS = {
    "site_title": "L'Fellah 2.0 Administration",
    "site_header": "L'Fellah",
    "site_brand": "L'FELLAH IOT",
    "site_logo": "core/img/logo.png",
    "custom_css": "core/css/jazzmin-fix.css",
    "welcome_sign": "Espace d'Administration - L'Fellah Agriculture IOT",
    "copyright": "L'Fellah Agriculture Connectée © 2026",
    "search_model": "core.plantscan",
    "show_sidebar": True,
    "navigation_expanded": True,
    "icons": {
        "accounts": "fas fa-users-cog",
        "accounts.user": "fas fa-user",
        "core": "fas fa-seedling",
        "core.plantscan": "fas fa-leaf",
        "core.alert": "fas fa-exclamation-triangle",
        "core.securitylog": "fas fa-shield-alt",
        "core.blockedip": "fas fa-ban",
        "core.report": "fas fa-file-pdf",
        "core.chatmessage": "fas fa-robot",
        "iot": "fas fa-microchip",
        "iot.device": "fas fa-server",
        "iot.sensorreading": "fas fa-thermometer-half",
        "iot.pumpcommand": "fas fa-water",
        "marketplace": "fas fa-store",
        "marketplace.product": "fas fa-box",
        "marketplace.order": "fas fa-shopping-cart",
        "subscriptions": "fas fa-credit-card",
        "subscriptions.plan": "fas fa-tags",
        "subscriptions.subscription": "fas fa-receipt",
    },
}

JAZZMIN_UI_TWEAKS = {
    "navbar_fixed": True,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "theme": "flatly",
    "dark_mode_theme": "darkly",
}


# ─── MENTIONS LEGALES MAROCAINES (FACTURES) ─────────────────────
LF_SOCIETE = {
    'raison_sociale': "L'FELLAH AGRICULTURE CONNECT\u00c9E SARL",
    'ice': '001234567000089',            # Identifiant Commun de l'Entreprise
    'rc': '98765',                        # Registre de Commerce
    'if_': '12345678',                    # Identifiant Fiscal
    'patente': '87654321',                # Numéro de Patente
    'adresse': 'Lot 12, Zone Agricole, 40000 Marrakech, Maroc',
    'telephone': '+212 5XX XX XX XX',
    'email': 'contact@lfellah.ma',
    'site_web': 'www.lfellah.ma',
    'capital': '100 000 MAD',
    'cnss': '9876543',                    # Affiliation CNSS
}
