from django.test import SimpleTestCase


class TestTranslationQueryset(SimpleTestCase):

    def test_save_translations(self):
        self.fail('please write test')
    # def save_translations(self, instance):
    #     to_update = [*instance.collect('updated')]
    #     if to_update:
    #         self.bulk_update((obj for obj in to_update if obj.value), ['value'])
    #         self.filter(pk__in=(obj.pk for obj in to_update if not obj.value)).delete()

    #     to_create = [*instance.collect('created')]
    #     if to_create:
    #         self.bulk_create(to_create)


class TestTranslation(SimpleTestCase):

    def test___str__(self):
        self.fail('please write test')
    # def __str__(self):
    #     return f'{self.content_object}.{self.field.name}.{self.lang} = "{self.value}"'

    def test_update(self):
        self.fail('please write test')

    def test_create(self):
        self.fail('please write test')


class TestTranslatableFieldQuerySet(SimpleTestCase):

    def test_patch_fields(self):
        self.fail('please write test')
    # def patch_fields(self):
    #     for field in self.all():
    #         field.patch_unpatch('patch')


class TestTranslatableField(SimpleTestCase):

    def test___str__(self):
        self.fail('please write test')
    # def __str__(self):
    #     return f'{self.content_type.model}|{self.title}'

    def test_save(self):
        self.fail('please write test')
    # def save(self, *args, **kwargs):
    #     super().save(*args, **kwargs)
    #     self.patch_unpatch('patch')

    def test_delete(self):
        self.fail('please write test')
    # def delete(self, *args, **kwargs):
    #     self.patch_unpatch('unpatch')
    #     super().delete(*args, **kwargs)

    def test_is_translatable(self):
        self.fail('please write test')
    # def is_translatable(self, value):
    #     return isinstance(value, self.translator_cls)

    def test_get_saved(self):
        self.fail('please write test')
    # def get_saved(self, instance):
    #     return instance.get_from_db.get(self.pk) or {}

    def test_collect(self):
        self.fail('please write test')
    # def collect(self, instance, action):
    #     value = vars(instance).get(self.name)
    #     if self.is_translatable(value):
    #         yield from getattr(self, f'collect_{action}')(self.get_saved(instance), value, instance)

    def test_collect_updated(self):
        self.fail('please write test')
    # def collect_updated(saved, value, *__):
    #     yield from (translation.update(lang, value) for lang, translation in saved.items() if translation.value != value.get(lang))

    def test_collect_created(self):
        self.fail('please write test')
    # def collect_created(self, saved, value, instance):
    #     model = getattr(self, 'translations').model
    #     yield from (model(self, instance, lang, value) for lang, value in value.iter if not saved.get(lang))

    def test___get__(self):
        self.fail('please write test')
    # def __get__(self, instance, instance_cls):
    #     if instance:
    #         value = vars(instance).get(self.name)
    #         if hasattr(instance, '_end_init') and not self.is_translatable(value):
    #             value = self.translator_cls().update(_origin=value, **self.get_saved(instance))
    #         return value
    #     return vars(instance_cls).get(self.name)

    def test___set__(self):
        self.fail('please write test')
    # def __set__(self, instance, value):
    #     if hasattr(instance, '_end_init') and not self.is_translatable(value):
    #         value = getattr(instance, self.name).update(value)
    #     vars(instance)[self.name] = value

    def test___delete__(self):
        self.fail('please write test')
    # def __delete__(self, instance):
    #     vars(instance).pop(self.name, None)

    def test_patch_unpatch(self):
        self.fail('please write test')
    # def patch_unpatch(self, patch):
    #     target_cls = getattr(self.content_type, 'model_class')()
    #     if target_cls:
    #         translations = getattr(self, f'{patch}_translations')(target_cls)
    #         getattr(self, f'{patch}_field')(target_cls, translations.fields)
    #         apply_mixins(patch, target_cls, translations.fields)

    def test_patch_translations(self):
        self.fail('please write test')
    # def patch_translations(target_cls):
    #     if not hasattr(target_cls, 'translations'):
    #         GenericRelation('tof.Translation', verbose_name=_('Translation')).contribute_to_class(target_cls, 'translations')
    #         target_cls.translations.fields = {}
    #     return target_cls.translations

    def test_unpatch_translations(self):
        self.fail('please write test')
    # def unpatch_translations(target_cls):
    #     return getattr(target_cls, 'translations', None)

    def test_patch_field(self):
        self.fail('please write test')
    # def patch_field(self, target_cls, fields):
    #     self.replaced_field = getattr(target_cls, self.name, None)
    #     setattr(target_cls, self.name, self)
    #     fields[self.pk] = self.name

    def test_unpatch_field(self):
        self.fail('please write test')

    # def unpatch_field(self, target_cls, fields):
    #     field = getattr(target_cls, self.name, None)
    #     setattr(target_cls, self.name, field.replaced_field)
    #     fields.pop(self.pk, None)


class TestLanguage(SimpleTestCase):

    def test___str__(self):
        self.fail('please write test')
    # def __str__(self):
    #     return f'{self.iso or str()}'


class TestStaticMessageTranslation(SimpleTestCase):

    def test___str__(self):
        self.fail('please write test')
    # def __str__(self):
    #     return f'{self.translation or self.message or str()}'

    def test___repr__(self):
        self.fail('please write test')
    # def __repr__(self):
    #     return f'{self!s} {self.langs()}'

    def test_langs(self):
        self.fail('please write test')
    # def langs(self):
    #     iterator = getattr(self.translation, 'iter', ())
    #     return ', '.join((lang for lang, __ in iterator)) if iterator else ''

    def test_gettext(self):
        self.fail('please write test')
    # @staticmethod
    # def gettext(translator, message):
    #     cls = StaticMessageTranslation
    #     import pdb; pdb.set_trace()
    #     if message not in cls.CACHE:
    #         try:
    #             cls.CACHE[message] = cls.objects.get_or_create(message=message)[0]
    #         except Exception as error:
    #             print(message, error)
    #             return str(message)
    #     cached = cls.CACHE[message]
    #     if not cached.translation.current:
    #         print(cached.translation)
    #         cached.translation = cls.base_translator_cls(translator, message) or message
    #         cached.save()
    #         print(cached.translation)
    #     return str(cached.translation)

    def test_patch_djangotranslation(self):
        self.fail('please write test')
    # @classmethod
    # def patch_djangotranslation(cls):
    #     DjangoTranslation.gettext = cls.gettext

    def test_save(self):
        self.fail('please write test')
    # def save(self, *args, **kwargs):
    #     super().save(*args, **kwargs)
    #     type(self).CACHE[self.message] = self
