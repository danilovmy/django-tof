# -*- coding: utf-8 -*-
from django.contrib.admin.options import ModelAdmin
from django.contrib.admin.sites import all_sites
from django.templatetags.i18n import GetAvailableLanguagesNode, settings
from django.utils.module_loading import import_string

from . import LANGUAGES_SOURCE
from .fields import TranslatableFieldFormField
from .utils import tof_class


class TofModelAdmin(ModelAdmin):
    pass


class ClassPatcherMixin:

    @classmethod
    def patch_bases(cls, target, *__):
        if not issubclass(target, cls):
            target = hasattr(target, '_meta') and getattr(target._meta, 'concrete_model', None) or target
            target.__bases__ = (cls, ) + target.__bases__


    @classmethod
    def unpatch_bases(cls, target, *args):
        fields = args and args[0]
        if not fields and issubclass(target, cls):
            target = hasattr(target, '_meta') and getattr(target._meta, 'concrete_model', None) or target
            target.__bases__ = tuple(base for base in target.__bases__ if base != cls)


class InstancePatcherMixin(ClassPatcherMixin):

    @classmethod
    def patch_bases(cls, target, *args):
        if not isinstance(target, cls):
            target.__class__ = tof_class(type(target), cls)

    @classmethod
    def unpatch_bases(cls, target, *args):
        fields = args and args[0]
        bases = type(target).__bases__
        if not fields and len(bases) == 2 and bases[0] is cls:
            original = bases[1]
            if type(target) is tof_class(original, cls):
                target.__class__ = original


class TranslationFieldModelFormMixin(ClassPatcherMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if hasattr(getattr(type(self.instance)._meta.concrete_model, name, None), 'replaced_field'):
                self.fields[name] = TranslatableFieldFormField((field,), required=False, initial=getattr(self.instance, name), label=field.label, help_text=field.help_text, label_suffix=field.label_suffix)

    def get_initial_for_field(self, field, field_name):
        initial = super().get_initial_for_field(field, field_name)
        if isinstance(field, TranslatableFieldFormField):
            initials = ((name.rpartition('_'), value) for name, value in (self.initial or {}).items() if name.startswith(f'{field_name}_'))
            for (name, splitter, lang), value in initials:
                if value and name == field_name:
                    initial[lang] = value
        return initial

class TranslationFieldMixin(ClassPatcherMixin):

    @classmethod
    def translatable_fields(cls):
        for name in dict.fromkeys(cls.translations.fields.values()):
            field = getattr(cls, name, None)
            if getattr(field, 'replaced_field', None):
                yield field

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._end_init = True

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if hasattr(self, 'translations'):
            self.translations._remove_prefetched_objects()
            self.translations.save_translations(self)

    def refresh_from_db(self, *args, **kwargs):
        getattr(self, '_prefetched_objects_cache', {}).pop('translations', None)
        return super().refresh_from_db(*args, **kwargs)

    def get_from_db(self, **kwargs):
        field_count = 0
        for field_count, field in enumerate(self.translatable_fields(), 1):
            saved = getattr(vars(self).get(field.name), '_tof_saved', None)
            if saved is not None:
                kwargs[field.pk] = saved
        if self._state.adding or len(kwargs) == field_count:
            return kwargs
        cache = vars(self).setdefault('_prefetched_objects_cache', {})
        for translation in cache.setdefault('translations', self.translations.all()):
            kwargs.setdefault(translation.field_id, {}).update({translation.lang_id: translation})
        return kwargs

    def collect(self, action):
        for field in self.translatable_fields():
            yield from field.collect(self, action)


class TofAdminMixin(InstancePatcherMixin):

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj=obj, change=change, **kwargs)
        TranslationFieldModelFormMixin.patch_bases(form)
        return form

    @classmethod
    def patch_unpatch(cls, patch, model, fields):
        for model_admin in cls.get_admins(model):
            getattr(cls, f'{patch}_bases')(model_admin, fields)

    @staticmethod
    def get_admins(model):
        yield from (site._registry[model] for site in all_sites if site.is_registered(model))


class TofInlineMixin(ClassPatcherMixin):
    _inlines_cache = {}

    def get_formset(self, request, obj=None, **kwargs):
        formset = super(TofInlineMixin, self).get_formset(request, obj=obj, **kwargs)
        TranslationFieldModelFormMixin.patch_bases(formset.form)
        return formset

    @classmethod
    def patch_unpatch(cls, patch, model, fields):
        for inline in cls.get_inlines(model):
            getattr(cls, f'{patch}_bases')(inline, fields)

    @classmethod
    def set_inlines(cls):
        for site in all_sites:
            for admin in site._registry.values():
                for inline in admin.inlines:
                    cls._inlines_cache[inline.model] = cls._inlines_cache.get(inline.model, set())
                    cls._inlines_cache[inline.model].add(inline)

    @classmethod
    def get_inlines(cls, model):
        if not cls._inlines_cache:
            cls.set_inlines()
        return cls._inlines_cache.get(model, tuple())


def apply_mixins(patch, target_cls, fields):
    """Add/remove to target_cls bases mixins, whose is necessary for work with tof."""
    getattr(TranslationFieldMixin, f'{patch}_bases')(target_cls, fields)
    TofAdminMixin.patch_unpatch(patch, target_cls, fields)
    TofInlineMixin.patch_unpatch(patch, target_cls, fields)


def load_languages(request):
    source = getattr(settings, 'LANGUAGES_SOURCE', LANGUAGES_SOURCE)
    if source and request:
        source = import_string(source)
        if hasattr(source, 'objects') and hasattr(source.objects, 'get_choices_by'):
            return source.objects.get_choices_by(request)


def wrapper(func):
    def wrapped(self, context):
        languages = load_languages(context.get('request'))
        if languages:
            context[self.variable] = languages
            return ''
        return func(self, context)
    return wrapped


GetAvailableLanguagesNode.render = wrapper(GetAvailableLanguagesNode.render)
