"""Isolated test project. All database connection options are environment based."""
import os
from importlib.util import find_spec

SECRET_KEY = 'tof-test-project-only'
DEBUG = True
ALLOWED_HOSTS = ['testserver', 'localhost']
INSTALLED_APPS = [
    'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages',
    'django.contrib.admin', 'tof', 'tests',
]
# An optional test dependency; its app provides the editor widget templates.
if find_spec('ckeditor') is not None:
    INSTALLED_APPS.append('ckeditor')
    CKEDITOR_UPLOAD_PATH = 'ckeditor-tests/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
USE_I18N = True
LANGUAGE_CODE = 'en'
LANGUAGES = [('de', 'German'), ('en', 'English'), ('fr', 'French'), ('it', 'Italian')]
STATIC_URL = '/static/'
ROOT_URLCONF = 'tests.urls'
MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]
DATABASES = {'default': {
    'ENGINE': os.environ.get('TOF_DB_ENGINE', 'django.db.backends.postgresql'),
    'NAME': os.environ.get('TOF_DB_NAME', 'tof_library'),
    'USER': os.environ.get('TOF_DB_USER', 'tof_test'),
    'PASSWORD': os.environ.get('TOF_DB_PASSWORD', ''),
    'HOST': os.environ.get('TOF_DB_HOST', '127.0.0.1'),
    'PORT': os.environ.get('TOF_DB_PORT', '5432'),
    'TEST': {'NAME': os.environ.get('TOF_TEST_DB_NAME', 'test_tof_library')},
}}
if DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
    DATABASES['default'] = {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}
