# -*- coding: utf-8 -*-
from django.contrib.admin.sites import all_sites
from django.db.models import Q
from .fields import TranslatableFieldFormField


class tofQ(Q):
    patch = True


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
        return not isinstance(target, cls) and super().patch_bases(type(target), *args)

    @classmethod
    def unpatch_bases(cls, target, *args):
        return isinstance(target, cls) and super().unpatch_bases(type(target), *args)


class TranslationManagerMixin(InstancePatcherMixin):

    def filter(self, *args, **kwargs):
        return self.run_function(super().filter, *args, **kwargs)

    def exclude(self, *args, **kwargs):
        return self.run_function(super().exclude, *args, **kwargs)

    def run_function(self, func, *args, **kwargs):
        query, changed = self.expand_arg(Q(*args, **kwargs))
        return func(query).distinct() if changed else func(tofQ(*args, **kwargs))

    def expand_arg(self, arg):
        if arg and not getattr(arg, 'patch', None):
            expanded = dict(self.expand_arg(child) if isinstance(child, Q) else (self.expand(*child) if isinstance(child, (list, tuple)) else (child, False)) for child in arg.children)
            if any(expanded.values()):
                return tofQ(*expanded.keys(), _connector=arg.connector, _negated=arg.negated), True
        return arg, False

    def expand(self, key, value):
        attribute, __, lookup = key.partition('__')
        field = getattr(self.model, attribute, None)
        if getattr(field, 'replaced_field', None):
            return tofQ((key, value), Q(**{f'translations__value__{lookup or "iexact"}'.strip('_'): value, 'translations__field_id': field.pk}), _connector=Q.OR), True
        return Q((key, value)), False

    def get_queryset(self, *args, **kwargs):
        response = super().get_queryset(*args, **kwargs)
        return response.prefetch_related('translations') if hasattr(self.model, 'translations') else response

    @classmethod
    def patch_bases(cls, target, *args):
        if not isinstance(target, cls) and target.auto_created:
            target.__class__ = type(f'{target.model.__name__}Manager', (type(target),), {})
        super().patch_bases(target, *args)

        if not issubclass(target._queryset_class, cls):
            target._queryset_class = type(f'{target.__class__.__name__}Queryset', (cls, target._queryset_class), {})

    @classmethod
    def unpatch_bases(cls, target, *args):
        super().unpatch_bases(target, *args)
        super().unpatch_bases(target._queryset_class, *args)


class TranslationFieldModelFormMixin(ClassPatcherMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if hasattr(getattr(type(self.instance)._meta.concrete_model, name, None), 'replaced_field'):
                self.fields[name] = TranslatableFieldFormField((field,), required=False, initial=getattr(self.instance, name), label=field.label, help_text=field.help_text, label_suffix=field.label_suffix)


class TranslationFieldMixin(ClassPatcherMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._end_init = True

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if hasattr(self, 'translations'):
            self.translations.save_translations(self)

    def get_from_db(self, **kwargs):
        for translation in self.translations.all():
            kwargs.setdefault(translation.field_id, {}).update({translation.lang_id: translation})
        self.translations._remove_prefetched_objects()
        return vars(self).setdefault('get_from_db', lambda *__, **___: kwargs)()  # made cached function

    def collect(self, action):
        for field in type(self).translations.fields.values():
            yield from getattr(type(self)._meta.concrete_model, field).collect(self, action)


class TofAdminMixin(InstancePatcherMixin):

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj=obj, change=change, **kwargs)
        TranslationFieldModelFormMixin.patch_bases(form)
        return form

    @classmethod
    def patch_unpatch(cls, patch, model, fields):
        for modeladmin in cls.get_admins(model):
            getattr(cls, f'{patch}_bases')(modeladmin, fields)

    @staticmethod
    def get_admins(model):
        yield from (site.get_admin(model) for site in all_sites if site.is_registered(model))


def apply_mixins(patch, target_cls, fields):
    """Add/remove to target_cls bases mixins, whose is necessary for work with tof."""
    getattr(TranslationFieldMixin, f'{patch}_bases')(target_cls, fields)
    getattr(TranslationManagerMixin, f'{patch}_bases')(target_cls.objects, fields)
    TofAdminMixin.patch_unpatch(patch, target_cls, fields)
