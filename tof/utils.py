# -*- coding: utf-8 -*-
# @Author: MaxST
# @Date:   2019-10-30 14:19:55
# @Last Modified by:   MaxST
# @Last Modified time: 2019-11-26 11:09:43
from django.utils.translation import get_language

from .settings import DEFAULT_LANGUAGE, FALLBACK_LANGUAGES, SITE_ID


class TranslatableText:
    def __init__(self, **kwargs):
        super().__init__()
        vars(self).update(**kwargs)

    def __getattr__(self, attr):
        if len(attr) == 2:
            attrs = vars(self)
            for lang in self.get_fallback_languages(attr):
                if lang in attrs:
                    return attrs[lang]
            return attrs.get('_origin') or ''
        raise AttributeError(attr)

    def __str__(self):
        return getattr(self, self.get_lang(), '')

    def __repr__(self):
        return str(self)

    def __html__(self):
        return str(self)

    def __eq__(self, other):
        return str(self) == str(other)

    def __add__(self, other):
        return f'{self}{other}'

    def __radd__(self, other):
        return f'{other}{self}'

    @staticmethod
    def get_lang():
        lang, *_ = get_language().partition('-')
        return lang

    def get_fallback_languages(self, attr):
        for fallback in (FALLBACK_LANGUAGES.get(attr) or (), FALLBACK_LANGUAGES.get(SITE_ID) or ()):
            yield from (lang for lang in fallback if lang != attr)
        yield DEFAULT_LANGUAGE
