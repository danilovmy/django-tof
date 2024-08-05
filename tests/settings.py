
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.contenttypes",
    "tof",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": 'django_tof',
    }
}

DEFAULT_LANGUAGE = 'en'