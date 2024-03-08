from django.utils import translation

default_translator = getattr(translation, 'gettext_lazy' if hasattr(translation, 'gettext_lazy') else 'ugettext_lazy')
get_language = translation.get_language
