from pathlib import Path

import dj_database_url
from django.contrib import messages
from environs import Env

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = Env()
env.read_env(str(BASE_DIR / ".env"), recurse=False)
if (BASE_DIR / ".env.dev").exists():
    env.read_env(str(BASE_DIR / ".env.dev"), recurse=False)
elif (BASE_DIR / ".env.prod").exists():
    env.read_env(str(BASE_DIR / ".env.prod"), recurse=False)

SECRET_KEY = env.str("SECRET_KEY", "dummy-build-only-key-not-used-in-runtime")
DEBUG = env.bool("DEBUG", False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", [])

# ============================================================================
# CORE DJANGO SETTINGS
# ============================================================================

INSTALLED_APPS = [
    # Channels must be before Django apps for proper ASGI support
    "daphne",
    # Third-party admin theme
    "unfold",
    # Django core apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Third-party apps
    "allauth",
    "allauth.account",
    "axes",
    "channels",
    "django_htmx",
    "heroicons",
    "storages",
    "widget_tweaks",
    # Local apps
    "apps.chat.apps.ChatConfig",
    "apps.properties.apps.PropertiesConfig",
    "apps.shared.apps.SharedConfig",
    "apps.users.apps.UsersConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "axes.middleware.AxesMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ============================================================================
# DATABASE
# ============================================================================

DATABASES = {
    "default": dj_database_url.parse(
        env.str("DATABASE_URL", "sqlite:///:memory:"),
        conn_max_age=env.int("DATABASE_CONN_MAX_AGE", 600),
    )
}

# ============================================================================
# AUTHENTICATION & AUTHORIZATION
# ============================================================================

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesBackend",
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

LOGIN_URL = "users:login"

# ============================================================================
# INTERNATIONALIZATION
# ============================================================================

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ============================================================================
# STATIC & MEDIA PATHS
# ============================================================================

STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_ROOT = BASE_DIR / "media"

# ============================================================================
# MESSAGES FRAMEWORK
# ============================================================================

MESSAGE_TAGS = {
    messages.DEBUG: "alert-info",
    messages.INFO: "alert-info",
    messages.SUCCESS: "alert-success",
    messages.WARNING: "alert-warning",
    messages.ERROR: "alert-danger",
}

# ============================================================================
# LOGGING
# ============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# ============================================================================
# MISCELLANEOUS
# ============================================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ============================================================================
# THIRD-PARTY INTEGRATION SETTINGS
# ============================================================================

from config.settings.allauth import *  # noqa: E402, F401, F403
from config.settings.axes import *  # noqa: E402, F401, F403
from config.settings.channels import *  # noqa: E402, F401, F403
from config.settings.storages import *  # noqa: E402, F401, F403
from config.settings.unfold import *  # noqa: E402, F401, F403
