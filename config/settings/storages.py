from environs import Env

env = Env()

MEDIA_URL = "/media/"
STATIC_URL = "static/"

USE_S3_MEDIA = env.bool("USE_S3_MEDIA", False)
USE_S3_STATIC = env.bool("USE_S3_STATIC", False)

AWS_HOST_NAME = env.str("AWS_HOST_NAME", "")
AWS_ACCESS_KEY_ID = env.str("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = env.str("AWS_SECRET_ACCESS_KEY", "")
AWS_S3_ENDPOINT_URL = env.str("AWS_S3_ENDPOINT_URL", "")
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = "public-read"
AWS_S3_VERIFY = env.bool("AWS_S3_VERIFY", True)
AWS_QUERYSTRING_AUTH = False

AWS_MEDIA_BUCKET_NAME = env.str("AWS_MEDIA_BUCKET_NAME", "realmkey-media")
AWS_STATIC_BUCKET_NAME = env.str("AWS_STATIC_BUCKET_NAME", "realmkey-static")

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

if USE_S3_MEDIA:
    AWS_S3_CUSTOM_DOMAIN = env.str(
        "AWS_S3_CUSTOM_DOMAIN",
        f"{AWS_MEDIA_BUCKET_NAME}.s3.amazonaws.com",
    )
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "bucket_name": AWS_MEDIA_BUCKET_NAME,
            "custom_domain": AWS_S3_CUSTOM_DOMAIN,
            "file_overwrite": AWS_S3_FILE_OVERWRITE,
            "default_acl": AWS_DEFAULT_ACL,
            "querystring_auth": AWS_QUERYSTRING_AUTH,
        },
    }
    if AWS_S3_ENDPOINT_URL:
        STORAGES["default"]["OPTIONS"]["endpoint_url"] = AWS_S3_ENDPOINT_URL
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"

if USE_S3_STATIC:
    AWS_S3_STATIC_CUSTOM_DOMAIN = env.str(
        "AWS_S3_STATIC_CUSTOM_DOMAIN",
        f"{AWS_STATIC_BUCKET_NAME}.s3.amazonaws.com",
    )
    STORAGES["staticfiles"] = {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "bucket_name": AWS_STATIC_BUCKET_NAME,
            "custom_domain": AWS_S3_STATIC_CUSTOM_DOMAIN,
            "file_overwrite": True,
            "default_acl": AWS_DEFAULT_ACL,
            "querystring_auth": False,
        },
    }
    if AWS_S3_ENDPOINT_URL:
        STORAGES["staticfiles"]["OPTIONS"]["endpoint_url"] = AWS_S3_ENDPOINT_URL
    STATIC_URL = f"https://{AWS_S3_STATIC_CUSTOM_DOMAIN}/"
