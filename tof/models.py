# -*- coding: utf-8 -*-

from django.db import models, transaction
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, QuerySet
from django.utils.safestring import mark_safe
from django.utils.translation.trans_real import DjangoTranslation

from .utils import TranslatableText
from . import default_translator as _
from .mixins import apply_mixins


class TranslationQueryset(QuerySet):

    @transaction.atomic
    def save_translations(self, instance):
        vars(instance).pop('get_from_db', None)
        to_update = [*instance.collect('updated')]
        self.bulk_update((obj for obj in to_update if obj.value), ['value'])
        self.bulk_delete((obj.pk for obj in to_update if not obj.value))
        self.bulk_create(instance.collect('created'))

    def bulk_delete(self, objs):
        return self.filter(pk__in=[*objs]).delete()


class Translation(models.Model):

    class Meta:
        verbose_name = _('Translation')
        verbose_name_plural = _('Translation')
        unique_together = ('object_id', 'field', 'lang')

    content_type = models.ForeignKey(ContentType, limit_choices_to=~Q(app_label='tof'), on_delete=models.DO_NOTHING, related_name='translations',)
    object_id = models.PositiveIntegerField(help_text=_('First set the field'))
    content_object = GenericForeignKey()

    field = models.ForeignKey('TranslatableField', related_name='translations', on_delete=models.DO_NOTHING)
    lang = models.ForeignKey('Language', related_name='translations', limit_choices_to=Q(is_active=True), on_delete=models.DO_NOTHING)
    value = models.TextField(_('Value'), help_text=_('Value field'))

    objects = TranslationQueryset.as_manager()

    def __str__(self):
        return f'{self.value or ""}'

    def __repr__(self):
        return f'{self.content_object}.{self.field.name}.{self.lang} = "{self}"'

    def update(self, lang, value):
        self.value = value[lang]
        return self

    @classmethod
    def create(cls, field, instance, lang, value):
        return cls(field=field, content_object=instance, lang_id=lang, value=value)


class TranslatableFieldQuerySet(QuerySet):

    def patch_fields(self):
        for field in self.all():
            field.patch_unpatch('patch')


class TranslatableField(models.Model):
    replaced_field = None
    translator_cls = TranslatableText

    class Meta:
        verbose_name = _('Translatable field')
        verbose_name_plural = _('Translatable fields')
        ordering = ('content_type', 'name')
        unique_together = ('content_type', 'name')

    name = models.CharField(_('Field name'), max_length=250, help_text=_('Name field'))
    content_type = models.ForeignKey(ContentType, limit_choices_to=~Q(app_label='tof'), on_delete=models.CASCADE, related_name='translatablefields')
    objects = TranslatableFieldQuerySet.as_manager()

    def __str__(self):
        return f'{self.content_type.model}|{self.name}'

    def pre_save(self, instance, *__):
        value = vars(instance).get(self.name)
        return getattr(value, '_origin', None) or value

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.patch_unpatch('patch')

    def delete(self, *args, **kwargs):
        self.patch_unpatch('unpatch')
        super().delete(*args, **kwargs)

    def is_translatable(self, value):
        return isinstance(value, self.translator_cls)

    def get_saved(self, instance):
        return instance.get_from_db().get(self.pk) or {}

    def collect(self, instance, action):
        value = vars(instance).get(self.name)
        if self.is_translatable(value):
            yield from getattr(self, f'collect_{action}')(self.get_saved(instance), value, instance)

    @staticmethod
    def collect_updated(saved, value, *__):
        yield from (translation.update(lang, value) for lang, translation in saved.items() if translation.value != value[lang])

    def collect_created(self, saved, value, instance):
        model = getattr(self, 'translations').model
        yield from (model.create(self, instance, lang, value) for lang, value in value.iter if not saved.get(lang))

    def __get__(self, instance, instance_cls):
        if instance:
            value = vars(instance).get(self.name)
            if hasattr(instance, '_end_init') and not self.is_translatable(value):
                value = self.translator_cls().update(_origin=value, **self.get_saved(instance))
            return value
        return vars(instance_cls).get(self.name)

    def __set__(self, instance, value):
        if hasattr(instance, '_end_init') and not self.is_translatable(value):
            value = getattr(instance, self.name).update_current(value)
        vars(instance)[self.name] = value

    def __delete__(self, instance):
        vars(instance).pop(self.name, None)

    def patch_unpatch(self, patch):
        target_cls = getattr(self.content_type, 'model_class')()
        if target_cls:
            if not hasattr(target_cls, 'translations'):
                GenericRelation('tof.Translation', verbose_name=_('Translation')).contribute_to_class(target_cls, 'translations')
                target_cls.translations.fields = {}
            getattr(self, f'{patch}_field')(target_cls, target_cls.translations.fields)
            apply_mixins(patch, target_cls, target_cls.translations.fields)

    def patch_field(self, target_cls, fields):
        if getattr(target_cls, self.name, None):
            self.replaced_field = getattr(target_cls, self.name, None)
            setattr(self.replaced_field.field, 'pre_save', lambda *args, **kwargs: self.pre_save(*args, *kwargs))
            setattr(target_cls, self.name, self)
            fields[self.pk] = self.name

    def unpatch_field(self, target_cls, fields):
        if getattr(target_cls, self.name, None):
            field = getattr(target_cls, self.name, None)
            delattr(field.replaced_field.field, 'pre_save')
            setattr(target_cls, self.name, field.replaced_field)
            fields.pop(self.pk, None)


class Language(models.Model):

    class Meta:
        verbose_name = _('Language')
        verbose_name_plural = _('Languages')
        ordering = ['iso']

    iso = models.CharField(max_length=2, unique=True, primary_key=True)
    is_active = models.BooleanField(_(u'Active'), default=True)

    def __str__(self):
        return f'{self.iso or str()}'


class StaticMessageTranslation(models.Model):
    CACHE = {}
    base_translator_cls = DjangoTranslation.gettext

    class Meta:
        verbose_name = _('Static translation')
        verbose_name_plural = _('Static translations')
        indexes = [models.Index(fields=['message'])]

    message = models.CharField(_('Message'), max_length=1000)
    translation = models.CharField(_('Translation'), max_length=1000)

    objects = QuerySet.as_manager()

    def __str__(self):
        return f'{self.translation or self.message or str()}'

    def languages(self):
        iterator = getattr(self.translation, 'iter', ())
        return ', '.join((lang for lang, __ in iterator)) if iterator else ''
    languages.admin_order_field = 'translations'

    @staticmethod
    def gettext(translator, message):
        cls = StaticMessageTranslation
        if message not in cls.CACHE:
            try:
                messages = cls.objects.filter(message=message)[:2]
                cls.CACHE[message] = messages[0] if len(messages) else cls.objects.create(message=message)
                if len(messages) > 1:
                    cls.objects.exclude(pk=cls.CACHE[message].pk).delete(message=message)
            except Exception as error:
                print(message, repr(error), error, getattr(error, 'args', None), error.__context__, error.__cause__,)
                return str(message)
        cached = cls.CACHE[message]
        if not cached.translation.current:
            translation = cls.base_translator_cls(translator, message)
            if translation not in vars(cached.translation).values():
                cached.translation = translation
                cached.save()
        return mark_safe(cached.translation)

    @classmethod
    def patch_djangotranslation(cls):
        DjangoTranslation.gettext = cls.gettext

    def save(self, *args, **kwargs):
        try:
            type(self).CACHE[self.message] = self
            super().save(*args, **kwargs)
        except Exception as error:
            type(self).CACHE.pop(self.message, None)
            raise Exception from error
