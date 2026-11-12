"""
Configuración de Donapp (Django).

Todos los valores sensibles o dependientes del entorno se leen del archivo .env
(ver .env.example). Nunca escribas contraseñas ni claves directamente aquí.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
    DB_HOST=(str, 'localhost'),
    DB_PORT=(str, '5432'),
)
environ.Env.read_env(BASE_DIR / '.env')

# ── Seguridad ────────────────────────────────────────────────────────────────
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')

# ── Aplicaciones ─────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ── Base de datos (PostgreSQL) ───────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT'),
    }
}

# ── Autenticación ────────────────────────────────────────────────────────────
AUTH_USER_MODEL = 'core.Usuario'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'index'
LOGOUT_REDIRECT_URL = 'login'

# El primer hasher es el que se usa para contraseñas nuevas. BCrypt va después
# para poder leer los hashes importados desde Laravel (formato "bcrypt$2b$...").
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.BCryptPasswordHasher',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 6}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Los enlaces de recuperación de contraseña duran 1 hora (igual que en Laravel).
PASSWORD_RESET_TIMEOUT = 60 * 60

# ── Internacionalización ─────────────────────────────────────────────────────
LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

# ── Archivos estáticos y multimedia ──────────────────────────────────────────
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Correo (Django 6.1: MAILERS reemplaza a los EMAIL_* obsoletos) ───────────
# Por defecto los correos se imprimen en la consola (útil en desarrollo).
# Para enviar de verdad, en el .env pon:
#   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
#   EMAIL_HOST=smtp.gmail.com
#   EMAIL_HOST_USER=...   EMAIL_HOST_PASSWORD=...   (EMAIL_PORT y EMAIL_USE_TLS opcionales)
_email_backend = env(
    'EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend'
)
MAILERS = {'default': {'BACKEND': _email_backend}}
if _email_backend.endswith('smtp.EmailBackend'):
    MAILERS['default']['OPTIONS'] = {
        'host': env('EMAIL_HOST'),
        'port': env.int('EMAIL_PORT', default=587),
        'use_tls': env.bool('EMAIL_USE_TLS', default=True),
        'username': env('EMAIL_HOST_USER', default=''),
        'password': env('EMAIL_HOST_PASSWORD', default=''),
    }

DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='Donapp <no-reply@donapp.local>')
