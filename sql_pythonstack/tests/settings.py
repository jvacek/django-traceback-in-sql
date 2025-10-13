"""Django settings for tests."""

import os

# BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production

DEBUG = True
SECRET_KEY = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"


INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]


# Database configuration
# Configured to work with tox's environment variables
DB_ENGINE = os.environ.get("DB_ENGINE", "")
DB_NAME = os.environ.get("DB_NAME", "")
DB_USER = os.environ.get("DB_USER", "")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_HOST = os.environ.get("DB_HOST", "")
DB_PORT = os.environ.get("DB_PORT", "")

# Configure database based on the test environment
if DB_ENGINE == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": DB_NAME or "django_sql_pythonstack_test",
            "USER": DB_USER or "postgres",
            "PASSWORD": DB_PASSWORD or "",
            "HOST": DB_HOST or "localhost",
            "PORT": DB_PORT or "5432",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": DB_NAME or ":memory:",
        }
    }
