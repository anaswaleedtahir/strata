from .base import *  # noqa: F401, F403

# ============================================================================
# DEBUG & DEVELOPMENT
# ============================================================================

DEBUG = True

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", ["localhost", "127.0.0.1"])  # noqa: F405

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://realmkey.loca.lt",
]

# ============================================================================
# DEVELOPMENT TOOLS
# ============================================================================

INSTALLED_APPS += [  # noqa: F405
    "debug_toolbar",
    "django_extensions",
]

MIDDLEWARE.insert(  # noqa: F405
    MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,  # noqa: F405
    "debug_toolbar.middleware.DebugToolbarMiddleware",
)

INTERNAL_IPS = [
    "127.0.0.1",
    "localhost",
]

# ============================================================================
# SECURITY (Relaxed for development)
# ============================================================================

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# ============================================================================
# AXES (Relaxed for development)
# ============================================================================

AXES_FAILURE_LIMIT = 10
AXES_COOLOFF_TIME = timedelta(seconds=10)  # noqa: F405

# ============================================================================
# LOGGING (More verbose in development)
# ============================================================================

LOGGING["loggers"]["apps"]["level"] = "DEBUG"  # noqa: F405
LOGGING["loggers"]["django.db.backends"] = {  # noqa: F405
    "handlers": ["console"],
    "level": "INFO",
    "propagate": False,
}

# ============================================================================
# EMAIL (Console backend for development)
# ============================================================================

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
