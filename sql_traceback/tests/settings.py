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

USE_TZ = True

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]


# Database configuration
# Configured to work with environment variables for testing different backends
DB_ENGINE = os.environ.get("DB_ENGINE", "sqlite")
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
            "NAME": DB_NAME or "django_traceback_in_sql_test",
            "USER": DB_USER or "testuser",
            "PASSWORD": DB_PASSWORD or "testpass",
            "HOST": DB_HOST or "localhost",
            "PORT": DB_PORT or "5432",
        }
    }
elif DB_ENGINE == "mysql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": DB_NAME or "django_traceback_in_sql_test",
            "USER": DB_USER or "testuser",
            "PASSWORD": DB_PASSWORD or "testpass",
            "HOST": DB_HOST or "localhost",
            "PORT": DB_PORT or "3306",
            "OPTIONS": {
                "charset": "utf8mb4",
            },
        }
    }
else:  # sqlite
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": DB_NAME or ":memory:",
        }
    }
