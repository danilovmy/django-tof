# -*- coding: utf-8 -*-
from . import DEFAULT_LANGUAGE, get_language


class TranslatableText(str):
    """Class like a string but returns values depends on get_language."""
    DEFAULT = DEFAULT_LANGUAGE

    def __setattr__(self, attr, value):
        vars(self)[attr] = str(value) if value else ''
        if not value and len(attr) == 2:
            delattr(self, attr)

    def __setitem__(self, attr, value):
        if isinstance(attr, str):
            setattr(self, attr, value)

    def __delattr__(self, attr):
        vars(self).pop(attr, None)

    def __delitem__(self, attr):
        if isinstance(attr, str):
            delattr(self, attr)

    def __getitem__(self, key):
        return getattr(self, key, None) if isinstance(key, str) else f'{self}'[key]

    def __str__(self):
        __, value = next(self.iter, (None, None))
        return f'{value or self["_origin"] or str()}'

    def __repr__(self):
        return f'{self} {vars(self).keys()}'

    def __eq__(self, other):
        return f'{self}' == f'{other}'

    def __add__(self, other):
        return f'{self}{other}'

    def __radd__(self, other):
        return f'{other}{self}'

    def __len__(self):
        return len(f'{self}')

    def __bool__(self):
        return bool(next(self.iter, None) or self['_origin'])

    def update(self, **kwargs):
        for attr, value in kwargs.items():
            setattr(self, attr, value)
        return self

    def __iter__(self):
        yield from str(self)

    @property
    def iter(self):
        langs = dict.fromkeys((self.get_lang(), self.DEFAULT, *(lang for lang in vars(self).keys() if len(lang) == 2)), )
        yield from ((lang, value) for lang, value in ((lang, getattr(self, lang, None)) for lang in langs) if value)

    @property
    def current(self):
        return getattr(self, self.get_lang(), None)

    def update_current(self, value):
        setattr(self, self.get_lang(), value)
        return self

    # TODO: make staticmethod a property
    @staticmethod
    def get_lang():
        lang = get_language() or 'en'
        return lang[:2]
