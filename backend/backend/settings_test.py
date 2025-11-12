# backend/settings_test.py
from .settings import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
}

WAYFORPAY_MERCHANT_ACCOUNT = "test_merchant"
WAYFORPAY_SECRET_KEY = "test_secret"
WAYFORPAY_MERCHANT_DOMAIN = "http://localhost"

DEEPL_API_KEY = "dummy_key"
