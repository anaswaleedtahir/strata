from .base import *  # noqa: F401, F403

# ============================================================================
# SECURITY
# ============================================================================

DEBUG = False

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")  # noqa: F405

CSRF_TRUSTED_ORIGINS = env.list(  # noqa: F405
    "CSRF_TRUSTED_ORIGINS",
    [
        "https://realmkey.duckdns.org",
        "http://realmkey.duckdns.org",
    ],
)

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", True)  # noqa: F405
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", 31536000)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", True)  # noqa: F405
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", True)  # noqa: F405
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"

# ============================================================================
# PERFORMANCE
# ============================================================================

TEMPLATES[0]["OPTIONS"]["loaders"] = [  # noqa: F405
    (
        "django.template.loaders.cached.Loader",
        [
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ],
    ),
]

# ============================================================================
# AXES (Stricter in production)
# ============================================================================

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(hours=1)  # noqa: F405

# ============================================================================
# LOGGING (Production-grade)
# ============================================================================

LOGGING["loggers"]["apps"]["level"] = "ERROR"  # noqa: F405
LOGGING["loggers"]["django"]["level"] = "WARNING"  # noqa: F405
LOGGING["loggers"]["django.security"] = {  # noqa: F405
    "handlers": ["console"],
    "level": "WARNING",
    "propagate": False,
}

# ============================================================================
# EMAIL
# ============================================================================

EMAIL_BACKEND = env.str(  # noqa: F405
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = env.str("EMAIL_HOST", "")  # noqa: F405
EMAIL_PORT = env.int("EMAIL_PORT", 587)  # noqa: F405
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", True)  # noqa: F405
EMAIL_HOST_USER = env.str("EMAIL_HOST_USER", "")  # noqa: F405
EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD", "")  # noqa: F405
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", "noreply@realmkey.com")  # noqa: F405

# ============================================================================
# ADMIN
# ============================================================================

ADMINS = env.list("ADMINS", [])  # noqa: F405
MANAGERS = ADMINS
