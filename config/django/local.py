from .base import *  # noqa: F401, F403

# ============================================================================
# DEBUG & DEVELOPMENT
# ============================================================================

DEBUG = True

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", ["localhost", "127.0.0.1"])  # noqa: F405

# Development and tests serve source assets directly. The manifest-backed
# storage remains the production default, where collectstatic creates it.
STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
}

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://strata.loca.lt",
]

# ============================================================================
# DEVELOPMENT TOOLS
# ============================================================================

INSTALLED_APPS += [  # noqa: F405
    "debug_toolbar",
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
