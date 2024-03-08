from os import getenv, environ
from django.conf import settings, ENVIRONMENT_VARIABLE
from django.utils import translation


environ[ENVIRONMENT_VARIABLE] = getenv(ENVIRONMENT_VARIABLE) or "tof.tests.settings"
default_translator = getattr(translation, 'gettext_lazy' if hasattr(translation, 'gettext_lazy') else 'ugettext_lazy')
get_language = translation.get_language

DEFAULT_LANGUAGE = getattr(settings, 'DEFAULT_LANGUAGE', None) or 'en'


# from tof import admin, fixtures, management, migrations, static, templates, tests, actions, apps, fields, forms, mixins, models, utils, views, widgets  # noqa

