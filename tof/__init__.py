from os import getenv
from django.conf import settings, ENVIRONMENT_VARIABLE
from django.utils import translation

default_translator = getattr(translation, 'gettext_lazy' if hasattr(translation, 'gettext_lazy') else 'ugettext_lazy')
get_language = translation.get_language

DEFAULT_LANGUAGE = getenv(ENVIRONMENT_VARIABLE) and getattr(settings, 'DEFAULT_LANGUAGE', None) or 'en'
