"""Regression tests against the standalone package schema."""

from . import test_query as fixture
from .fixtures import TranslationFixture

from django.contrib import admin
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils.translation import override

from tof.models import Translation
from tof.utils import TranslatableText


class SimplificationTests(TranslationFixture):

    def uncached_item(self, pk):
        return fixture.QueryItem.from_db(connection.alias, ['id', 'title', 'description', 'number'],
                                         [pk, 'Origin', 'Source', 0])

    def test_fallback_read_is_cached_including_empty_results(self):
        for pk in (1, 4):
            with self.subTest(pk=pk):
                item = self.uncached_item(pk)
                with CaptureQueriesContext(connection) as queries:
                    first = item.get_from_db()
                    second = item.get_from_db()
                self.assertEqual(first, second)
                self.assertEqual(len(queries), 1)
                if pk == 1:
                    self.assertEqual(first[910001]['de'].value, 'Zulu')
                else:
                    self.assertEqual(first, {})

    def test_save_invalidates_fallback_cache_including_empty_results(self):
        for pk in (1, 4):
            with self.subTest(pk=pk), override('de'):
                item = self.uncached_item(pk)
                item.get_from_db()
                item.title = 'Saved title'
                item.save()
                with CaptureQueriesContext(connection) as queries:
                    first = item.get_from_db()
                    second = item.get_from_db()
                self.assertEqual(first[910001]['de'].value, 'Saved title')
                self.assertEqual(first, second)
                self.assertEqual(len(queries), 1)
                self.assertEqual(Translation.objects.get(object_id=pk, field_id=910001, lang_id='de').value,
                                 'Saved title')

    def test_full_and_partial_refresh_invalidate_fallback_cache(self):
        for fields in (None, ['title'], ['number']):
            Translation.objects.filter(object_id=4).delete()
            for pk in (1, 4):
                with self.subTest(fields=fields, pk=pk):
                    item = self.uncached_item(pk)
                    item.get_from_db()
                    Translation.objects.update_or_create(object_id=pk, field_id=910001, lang_id='de',
                                                         defaults={'content_type_id': self.content_type.pk, 'value': str(fields)})
                    with CaptureQueriesContext(connection) as queries:
                        item.refresh_from_db(fields=fields)
                        first = item.get_from_db()
                        second = item.get_from_db()
                    self.assertEqual(first[910001]['de'].value, str(fields))
                    self.assertEqual(first, second)
                    self.assertEqual(len(queries), 1 if fields is None else 2)

    def test_create_and_update_keep_origin_and_translations(self):
        with override('de'):
            item = fixture.QueryItem.objects.create(
                title=TranslatableText().update(_origin='Source title', de='Neuer Titel', en='New title'),
                description='Source description',
            )
            self.assertIsNotNone(item.pk)
            fresh = fixture.QueryItem.objects.get(pk=item.pk)
            self.assertEqual(fresh.title['_origin'], 'Source title')
            self.assertEqual(dict(fresh.title.iter), {'de': 'Neuer Titel', 'en': 'New title'})
            self.assertEqual(fresh.description['_origin'], 'Source description')
            fresh.title = 'Geänderter Titel'
            fresh.save(update_fields=['title'])
            fresh.refresh_from_db()
            self.assertEqual(fresh.title['_origin'], 'Source title')
            self.assertEqual(dict(fresh.title.iter), {'de': 'Geänderter Titel', 'en': 'New title'})

    def test_bulk_create_preserves_translated_field_origins(self):
        items = fixture.QueryItem.objects.bulk_create([
            fixture.QueryItem(title=TranslatableText().update(_origin='Source title', de='Neuer Titel')),
            fixture.QueryItem(title=None),
        ])
        fresh = list(fixture.QueryItem.objects.filter(pk__in=[item.pk for item in items]).order_by('pk'))
        self.assertEqual([item.title['_origin'] for item in fresh], ['Source title', None])
        self.assertEqual([item.description['_origin'] for item in fresh], ['', ''])

    def test_mixed_fields_update_create_delete_and_repeated_save(self):
        with override('de'):
            item = fixture.QueryItem.objects.get(pk=1)
            item.title.update(de='Changed title', en='', it='New title')
            item.description.update(de='', en='New description')
            item.save()
            expected = {
                (910001, 'de'): 'Changed title', (910001, 'fr'): 'Autre',
                (910001, 'it'): 'New title', (910002, 'en'): 'New description',
            }
            rows = item.translations.values_list('field_id', 'lang_id', 'value')
            self.assertEqual({(field, lang): value for field, lang, value in rows}, expected)
            self.assertEqual(set(item.title._tof_saved), {'de', 'fr', 'it'})
            self.assertEqual(set(item.description._tof_saved), {'en'})
            self.assertIsNot(item.title._tof_saved, item.description._tof_saved)
            for field in item.translatable_fields():
                for saved in getattr(item, field.name)._tof_saved.values():
                    self.assertEqual(saved.field_id, field.pk)
                    self.assertIsNotNone(saved.pk)
                    self.assertFalse(saved._state.adding)
            with CaptureQueriesContext(connection) as queries:
                item.save()
            self.assertFalse(any(q['sql'].startswith(('INSERT', 'UPDATE "tof_translation"', 'DELETE')) for q in queries))
            self.assertEqual(item.translations.count(), len(expected))
            item.title.update(it='Changed again')
            item.description.update(en='')
            item.save()
            self.assertEqual(item.title._tof_saved['it'].value, 'Changed again')
            self.assertEqual(item.description._tof_saved, {})

    def test_first_translations_and_deferred_origin_are_isolated(self):
        with override('de'):
            item = fixture.QueryItem.objects.get(pk=4)
            item.title = 'First title'
            item.description = 'First description'
            item.save()
            self.assertEqual(item.title._tof_saved['de'].field_id, 910001)
            self.assertEqual(item.description._tof_saved['de'].field_id, 910002)
            item = fixture.QueryItem.objects.only('id', 'title').get(pk=4)
            item.title = 'Second title'
            with CaptureQueriesContext(connection) as queries:
                item.save(update_fields=['title'])
            self.assertNotIn('description', vars(item))
            self.assertFalse(any('"tof_test_item"."description"' in q['sql'] for q in queries))
            self.assertEqual(item.title['_origin'], 'Only origin')
            fresh = fixture.QueryItem.objects.get(pk=4)
            self.assertEqual(fresh.title['_origin'], 'Only origin')
            self.assertEqual(fresh.description['de'], 'First description')
            self.assertNotIn('_tof_saved', dict(item.title.iter))

    def test_translation_admin_prefetch_hydrates_all_target_fields(self):
        from tof.admin import TranslationAdmin
        model_admin = TranslationAdmin(Translation, admin.AdminSite())
        Translation.objects.bulk_create([
            Translation(content_type_id=self.content_type.pk, object_id=4, field_id=910001, lang_id='de', value='New title'),
            Translation(content_type_id=self.content_type.pk, object_id=999, field_id=910001, lang_id='de', value='Missing target'),
        ])
        with override('de'), CaptureQueriesContext(connection) as queries:
            rows = list(model_admin.get_queryset(None).filter(object_id__in=[1, 4, 999]).order_by('pk'))
            targets = [row.content_object for row in rows if row.object_id == 1]
            self.assertEqual([str(target.title) for target in targets], ['Zulu'] * 4)
            self.assertEqual(targets[0].title['fr'], 'Autre')
            self.assertEqual(targets[0].description['de'], 'Beschreibung')
            self.assertEqual(targets[0].get_from_db()[910001]['en'].value, 'Alpha')
            empty_field_target = next(row.content_object for row in rows if row.object_id == 4)
            self.assertEqual(empty_field_target.description['_origin'], '')
            self.assertEqual(empty_field_target.description._tof_saved, {})
            self.assertIsNone(next(row.content_object for row in rows if row.object_id == 999))
        self.assertEqual(len(queries), 2)
