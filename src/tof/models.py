from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.db.models import Q, QuerySet
from django.utils.safestring import mark_safe
from django.utils.translation.trans_real import DjangoTranslation

from . import _, activate_language, get_language
from .mixins import apply_mixins
from .utils import TranslatableText


class TranslationQueryset(QuerySet):

    @transaction.atomic
    def save_translations(self, instance):
        # Loading uses the compiler snapshot; writes deliberately re-read current rows.
        saved = {}
        for obj in self.filter():
            saved.setdefault(obj.field_id, {})[obj.lang_id] = obj
        for field in instance.translatable_fields():
            value = vars(instance).get(field.name)
            if isinstance(value, TranslatableText):
                vars(value)['_tof_saved'] = saved.setdefault(field.pk, {})
        to_update = [*instance.collect('updated')]
        self.bulk_update((obj for obj in to_update if obj.value), ['value'])
        self.filter(pk__in=(obj.pk for obj in to_update if not obj.value)).delete()
        created = self.bulk_create(instance.collect('created'))
        for obj in (*to_update, *created):
            if obj.value:
                saved[obj.field_id][obj.lang_id] = obj
            else:
                saved[obj.field_id].pop(obj.lang_id, None)

class Translation(models.Model):

    class Meta:
        verbose_name = _('Translation')
        verbose_name_plural = _('Translation')
        unique_together = ('object_id', 'field', 'lang')

    content_type = models.ForeignKey(ContentType, limit_choices_to=~Q(app_label='tof'), on_delete=models.DO_NOTHING, related_name='translations',)
    object_id = models.PositiveIntegerField(help_text=_('First set the field'))
    content_object = GenericForeignKey()

    field = models.ForeignKey('TranslatableField', related_name='translations', on_delete=models.CASCADE)
    lang = models.ForeignKey('Language', related_name='translations', to_field='iso', limit_choices_to=Q(is_active=True), on_delete=models.DO_NOTHING)
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
        for field in self.select_related('content_type'):
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

    def pre_save(self, instance, *args, **kwargs):
        value = vars(instance).get(self.name)
        return value['_origin'] if self.is_translatable(value) else value

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.patch_unpatch('patch')

    def delete(self, *args, **kwargs):
        self.patch_unpatch('unpatch')
        super().delete(*args, **kwargs)

    def is_translatable(self, value):
        return isinstance(value, self.translator_cls)

    def get_saved(self, instance):
        saved = getattr(vars(instance).get(self.name), '_tof_saved', None)
        if saved is not None:
            return saved
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
            if self.name not in vars(instance):
                self.replaced_field.__get__(instance, instance_cls)
            value = vars(instance).get(self.name)
            if hasattr(instance, '_end_init') and not self.is_translatable(value):
                value = self.translator_cls().update(_origin=value, **self.get_saved(instance))
            return value
        return self

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
            self._inherited_descriptor = self.name not in vars(target_cls)
            self.translation_content_type_id = self.content_type_id
            if target_cls._meta.proxy:
                original = getattr(target_cls._meta.concrete_model, self.name, None)
                self.translation_content_type_id = getattr(original, 'translation_content_type_id', None) or ContentType.objects.get_for_model(target_cls).pk
            self.replaced_field = getattr(target_cls, self.name, None)
            if isinstance(self.replaced_field, TranslatableField):
                self.replaced_field = self.replaced_field.replaced_field
            self.replaced_field.field.pre_save = self.pre_save
            setattr(target_cls, self.name, self)
            fields[self.pk] = self.name

    def unpatch_field(self, target_cls, fields):
        if getattr(target_cls, self.name, None):
            field = getattr(target_cls, self.name, None)
            if hasattr(field, 'replaced_field'):
                original = getattr(target_cls._meta.concrete_model, self.name, None)
                if original is not field and isinstance(original, TranslatableField):
                    field.replaced_field.field.pre_save = original.pre_save
                elif 'pre_save' in vars(field.replaced_field.field):
                    delattr(field.replaced_field.field, 'pre_save')
                if getattr(field, '_inherited_descriptor', False):
                    delattr(target_cls, self.name)
                else:
                    setattr(target_cls, self.name, field.replaced_field)
            fields.pop(self.pk, None)

    def set_values(self, obj, **values):
        current_lang = get_language()
        for lang, value in values.items():
            activate_language(lang)
            setattr(obj, self.name, value)
        activate_language(current_lang)


class LanguageQuerySet(QuerySet):

    def active(self):
        return self.filter(is_active=True)

    def get_choices_by(self, *args, **kwargs):
        return ((obj.iso, str(obj)) for obj in self.active())


class Language(models.Model):

    class Meta:
        verbose_name = _('Language')
        verbose_name_plural = _('Languages')
        ordering = ['iso']

    iso = models.CharField(max_length=2, unique=True)
    is_active = models.BooleanField(_('Active'), default=True)

    objects = LanguageQuerySet.as_manager()

    def __str__(self):
        return f'{self.iso or ""}'


class ThroughLanguage(models.Model):

    class Meta:
        abstract = True

    language = models.ForeignKey(Language, on_delete=models.CASCADE, to_field='iso', limit_choices_to=Q(is_active=True))


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
        return f'{self.translation or self.message or ""}'

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
                if len(messages):
                    cls.CACHE[message], *messages = messages
                    if messages:
                        cls.objects.exclude(pk=cls.CACHE[message].pk).filter(message=message).delete()
                else:
                    cls.CACHE[message] = cls.objects.create(message=message)
            except Exception as error:
                print(message, repr(error), error, getattr(error, 'args', None), error.__context__, error.__cause__,)
                return str(message)
        cached = cls.CACHE[message]
        if not isinstance(cached.translation, TranslatableText):
            cached.translation = TranslatableText()
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

