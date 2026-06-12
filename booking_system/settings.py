import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-o5#v%*6u%o@)2w0hbw%&#m_bapr!ys8uw0&^d9z%fz(o55injt")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"
DEFAULT_ALLOWED_HOSTS = "127.0.0.1,localhost,testserver"
render_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME")
vercel_hostname = os.getenv("VERCEL_URL")
allowed_host_values = [os.getenv("DJANGO_ALLOWED_HOSTS", DEFAULT_ALLOWED_HOSTS), render_hostname, vercel_hostname]
ALLOWED_HOSTS = [host.strip().replace("https://", "").replace("http://", "") for value in allowed_host_values if value for host in value.split(",") if host.strip()]
if not DEBUG and SECRET_KEY.startswith("django-insecure-"):
    raise RuntimeError("DJANGO_SECRET_KEY must be set to a secure value when DJANGO_DEBUG=false.")


def parse_allowed_origins(env_var: str, default: str) -> list[str]:
    origins = []
    for origin in os.getenv(env_var, default).split(","):
        cleaned = origin.strip()
        if not cleaned or cleaned == "*":
            continue
        origins.append(cleaned)
    return origins


def origin_values(*values: str | None) -> list[str]:
    origins: list[str] = []
    for value in values:
        if not value:
            continue
        for origin in value.split(","):
            cleaned = origin.strip().rstrip("/")
            if not cleaned or cleaned == "*":
                continue
            if not cleaned.startswith(("http://", "https://")):
                cleaned = f"https://{cleaned}"
            origins.append(cleaned)
    return origins

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'corsheaders',
    'drf_spectacular',
    'rest_framework',

    'careconnect_v2_api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'booking_system.urls'

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

WSGI_APPLICATION = 'booking_system.wsgi.application'

if os.getenv("DATABASE_URL"):
    DATABASES = {
        "default": dj_database_url.config(
            conn_max_age=int(os.getenv("POSTGRES_CONN_MAX_AGE", "60")),
            conn_health_checks=True,
            ssl_require=os.getenv("DATABASE_SSL_REQUIRE", "true").lower() == "true",
        )
    }
elif os.getenv("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB"),
            "USER": os.getenv("POSTGRES_USER", "postgres"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": int(os.getenv("POSTGRES_CONN_MAX_AGE", "60")),
            "OPTIONS": {
                "application_name": "booking_system",
            },
        }
    }
elif DEBUG:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    raise RuntimeError("DATABASE_URL or POSTGRES_* settings must be configured when DJANGO_DEBUG=false.")
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
LANGUAGE_CODE = 'en-us'
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "Africa/Johannesburg")

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "login": "5/hour",
        "register": "5/hour",
        "password_reset": "3/hour",
        "booking": "20/hour",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "booking_system.api_exception_handler.custom_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "CareConnect API",
    "DESCRIPTION": "OpenAPI schema for the CareConnect appointment booking backend.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "true" if not DEBUG else "false").lower() == "true"
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "true" if not DEBUG else "false").lower() == "true"
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "false").lower() == "true"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0" if DEBUG else "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "true").lower() == "true"
SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "true").lower() == "true"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

DEFAULT_CELERY_BROKER_URL = "redis://localhost:6379/0" if DEBUG else "memory://"
DEFAULT_CELERY_RESULT_BACKEND = "redis://localhost:6379/0" if DEBUG else "cache+memory://"
REDIS_URL = os.getenv("REDIS_URL", DEFAULT_CELERY_BROKER_URL)
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", DEFAULT_CELERY_RESULT_BACKEND))

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = sorted(set(parse_allowed_origins(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:5174,http://127.0.0.1:5174,http://localhost:5175,http://127.0.0.1:5175,http://localhost:8080,http://127.0.0.1:8080",
) + origin_values(os.getenv("FRONTEND_URL"), os.getenv("GREENCHOICE_FRONTEND_URL"))))
CSRF_TRUSTED_ORIGINS = sorted(set(parse_allowed_origins(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:5174,http://127.0.0.1:5174,http://localhost:5175,http://127.0.0.1:5175,http://localhost:8080,http://127.0.0.1:8080",
) + origin_values(os.getenv("FRONTEND_URL"), os.getenv("GREENCHOICE_FRONTEND_URL"))))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "booking_system": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}
