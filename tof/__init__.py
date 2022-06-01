# -*- coding: utf-8 -*-
from django.conf import settings
from settings import get_language, default_translator

DEFAULT_LANGUAGE = getattr(settings, 'DEFAULT_LANGUAGE', 'en') or 'en'
