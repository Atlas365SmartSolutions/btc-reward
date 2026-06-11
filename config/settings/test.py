from __future__ import annotations

from config.settings.development import *  # noqa: F403
from config.settings.development import MIDDLEWARE as DEVELOPMENT_MIDDLEWARE

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
STORAGES = {"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}
MIDDLEWARE = [
    middleware for middleware in DEVELOPMENT_MIDDLEWARE if middleware != "whitenoise.middleware.WhiteNoiseMiddleware"
]
