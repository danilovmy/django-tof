# -*- coding: utf-8 -*-
from django.core.exceptions import ValidationError
from django.forms.fields import MultiValueField

from .widgets import TranslatableFieldHiddenWidget, TranslatableFieldWidget
from .utils import TranslatableText


class TranslatableFieldFormField(MultiValueField):
    widget = TranslatableFieldWidget
    hidden_widget = TranslatableFieldHiddenWidget
    cleaned_langs = None

    def __init__(self, fields, *args, **kwargs):
        kwargs['widget'] = self.widget([field.widget for field in fields])
        kwargs['require_all_fields'] = any(field.required for field in fields)
        super().__init__(fields, *args, **kwargs)
        self.initial = self.initial or TranslatableText()

    def compress(self, data_list):
        if not data_list and self.require_all_fields:
            raise ValidationError(self.error_messages['required'], code='required')
        return TranslatableText().update(_origin=self.initial['_origin'], **dict(zip(self.cleaned_langs or [], data_list or [])))

    def clean(self, values):
        if values and isinstance(values, (list, tuple)):
            values = {str(lang)[:2]: text for lang, text in values}
            self.cleaned_langs, values = list(values.keys()), list(values.values())
            self.fields = self.fields * len(values)
        return super().clean(values)
