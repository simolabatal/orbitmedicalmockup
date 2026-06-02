from .base import *

import pymysql
pymysql.install_as_MySQLdb()

DEBUG = True

# Multi-DB Offline-First (HA)
#   default = SQLite  (toujours disponible, auth/admin + fallback)
#   mysql   = MySQL   (XAMPP, primaire pour les donnees IoT)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    },
    'mysql': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('MYSQL_DB', default='lfellah_db'),
        'USER': config('MYSQL_USER', default='root'),
        'PASSWORD': config('MYSQL_PASSWORD', default=''),
        'HOST': config('MYSQL_HOST', default='127.0.0.1'),
        'PORT': config('MYSQL_PORT', default='3306'),
        'OPTIONS': {
            'connect_timeout': 3,
            'charset': 'utf8mb4',
        },
    },
}

DATABASE_ROUTERS = ['core.db_router.PrimaryReplicaRouter']

# Exécution synchrone des tâches Celery (pas besoin de Redis en dev)
CELERY_TASK_ALWAYS_EAGER = True

# Clés API pour le développement
# ROTATED — les clés sont désormais lues depuis le fichier .env via config()
GEMINI_API_KEY = config('GEMINI_API_KEY', default='')
OPENWEATHER_API_KEY = config('OPENWEATHER_API_KEY', default='')

# Email — lit depuis .env (SMTP Gmail par défaut)
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
