"""PostgreSQL regressions against the installed package and its real schema."""
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.models import Count, F, OuterRef, Q, Subquery
from django.db.models.functions import Lower
from django.db.models.sql.compiler import SQLCompiler
from django.db.models.sql.query import Query
from django.test.utils import CaptureQueriesContext
from django.utils.translation import override

from tof.models import TranslatableField, Translation
from tof import query
from tof.utils import TranslatableText


from .models import QueryItem, QueryLink, QueryItemProxy
from .fixtures import TranslationFixture


class QueryCompilerTests(TranslationFixture):
    def ids(self, qs):
        return list(qs.order_by('pk').values_list('pk', flat=True))

    def test_hydration_all_languages_origin_and_no_eav_select(self):
        with CaptureQueriesContext(connection) as queries, override('de'):
            item = QueryItem.objects.get(pk=1)
            self.assertEqual(str(item.title), 'Zulu')
            self.assertEqual(item.title['en'], 'Alpha')
            self.assertEqual(item.title['fr'], 'Autre')
            self.assertEqual(item.title['_origin'], 'Origin A')
            self.assertEqual(str(item.description), 'Beschreibung')
            self.assertEqual(item.get_from_db()[910001]['de'].pk, 1)
        self.assertEqual(len(queries), 1)
        self.assertEqual(queries[0]['sql'].count('JOIN LATERAL'), 1)
        only_ids = QueryLink.objects.filter(item__description__contains='schreib').order_by('item__title').values_list('pk', flat=True)
        self.assertEqual(list(only_ids), [1])
        sql = only_ids.query.sql_with_params()[0]
        self.assertEqual(sql.count('JOIN LATERAL'), 1)
        self.assertNotIn('JSONB_AGG', sql)
        self.assertFalse(QueryItem.objects.all()._prefetch_related_lookups)

    def test_translated_order_before_pagination_and_language_recompile(self):
        query = QueryItem.objects.order_by('title').query
        with override('de'):
            self.assertEqual(list(QueryItem.objects.order_by('title').values_list('pk', flat=True)[:2]), [2, 3])
            first = query.sql_with_params()
            self.assertEqual(first, query.sql_with_params())
        with override('en'):
            self.assertEqual(list(QueryItem.objects.order_by('title').values_list('pk', flat=True)[:2]), [1, 2])
            self.assertNotEqual(first[1], query.sql_with_params()[1])
        self.assertFalse(hasattr(query, '_tof_plan'))

    def test_q_exact_in_contains_and_nullable_exclusion(self):
        self.assertEqual(self.ids(QueryItem.objects.filter(title='Zulu')), [1])
        self.assertEqual(self.ids(QueryItem.objects.filter(title='zulu')), [1])
        self.assertEqual(self.ids(QueryItem.objects.filter(title__exact='zulu')), [])
        self.assertEqual(self.ids(QueryItem.objects.filter(title__iexact='zulu')), [1])
        self.assertEqual(self.ids(QueryItem.objects.filter(title__in=['Autre'])), [1, 2])
        self.assertEqual(self.ids(QueryItem.objects.filter(Q(title__icontains='GAM') | Q(description__contains='schreib'))), [1, 3])
        self.assertEqual(self.ids(QueryItem.objects.exclude(title__contains='Gamma')), [1, 2, 4])
        self.assertEqual(self.ids(QueryItem.objects.exclude(title='unrelated')), [1, 2, 3, 4])
        self.assertEqual(self.ids(QueryItem.objects.filter(title='Origin A')), [1])

    def test_related_filter_order_and_select_related_hydration(self):
        with CaptureQueriesContext(connection) as queries, override('de'):
            links = list(QueryLink.objects.select_related('item').filter(item__title__icontains='a').order_by('item__title'))
            self.assertEqual([link.item_id for link in links], [2, 3, 1])
            self.assertEqual(str(links[-1].item.title), 'Zulu')
            self.assertEqual(links[-1].item.title['fr'], 'Autre')
        self.assertEqual(len(queries), 1)
        self.assertEqual(queries[0]['sql'].count('JOIN LATERAL'), 1)

    def test_deferred_field_load_hydrates_in_one_reload(self):
        with CaptureQueriesContext(connection) as queries, override('de'):
            item = QueryItem.objects.only('id', 'title').get(pk=1)
            self.assertEqual(str(item.title), 'Zulu')
            self.assertEqual(len(queries), 1)
            self.assertEqual(str(item.description), 'Beschreibung')
            self.assertEqual(len(queries), 2)
            self.assertEqual(item.description['_origin'], 'Source A')

    def test_functions_values_grouping_and_scalar_subquery(self):
        with override('de'):
            self.assertEqual(QueryItem.objects.annotate(lower=Lower('title')).get(pk=1).lower, 'zulu')
            copy = QueryItem.objects.annotate(copy=F('title')).get(pk=1).copy
            self.assertEqual(copy, 'Zulu')
            self.assertNotIsInstance(copy, TranslatableText)
            self.assertEqual(list(QueryItem.objects.filter(pk__lte=2).order_by('pk').values_list('title', flat=True)), ['Zulu', 'Beta'])
            grouped = list(QueryItem.objects.values('title').annotate(total=Count('pk')).order_by('title'))
            self.assertTrue(all(isinstance(row['title'], (str, type(None))) for row in grouped))
            self.assertEqual(QueryItem.objects.annotate(total=Count('querylink')).get(pk=1).total, 1)
            self.assertEqual([item.pk for item in QueryItem.objects.annotate(total=Count('querylink')).order_by('title')[:2]], [2, 3])
            source = QueryItem.objects.filter(pk=OuterRef('item_id')).values('title')[:1]
            self.assertEqual(QueryLink.objects.annotate(translated=Subquery(source)).get(pk=1).translated, 'Zulu')
            sql = QueryLink.objects.annotate(translated=Subquery(source)).query.sql_with_params()[0]
            self.assertNotIn('JSONB_BUILD_ARRAY', sql.split('FROM "tof_test_link"')[0])

    def test_write_origin_translation_metadata_and_translated_update(self):
        with override('de'):
            item = QueryItem.objects.get(pk=1)
            item.title = 'Changed'
            item.save()
            item.title = 'Again'
            item.save()
            self.assertEqual(QueryItem.objects.get(pk=1).title['de'], 'Again')
            self.assertEqual(QueryItem.objects.get(pk=1).title['_origin'], 'Origin A')
            self.assertEqual(QueryItem.objects.filter(title='Gamma').update(number=9), 1)
            self.assertEqual(QueryItem.objects.get(pk=3).number, 9)

    def test_save_keeps_empty_null_origin_and_deferred_fields(self):
        with override('de'):
            item = QueryItem.objects.only('id', 'title').get(pk=3)
            item.title = 'Translated null'
            with CaptureQueriesContext(connection) as queries:
                item.save(update_fields=['title'])
            self.assertNotIn('description', item.__dict__)
            self.assertFalse(any('"tof_test_item"."description"' in q['sql'] for q in queries))
            self.assertIsNone(QueryItem.objects.get(pk=3).title['_origin'])
            QueryItem.objects.filter(pk=3).update(title='')
            item = QueryItem.objects.get(pk=3)
            item.title = 'Translated empty'
            item.save()
            self.assertEqual(QueryItem.objects.get(pk=3).title['_origin'], '')

    def test_proxy_uses_concrete_object_ct_and_proxy_field_id(self):
        content_type = ContentType.objects.get_for_model(QueryItemProxy, for_concrete_model=False)
        descriptor = TranslatableField.objects.create(id=910003, name='title', content_type=content_type)
        try:
            Translation.objects.create(content_type_id=self.content_type.pk, object_id=2, field_id=910003, lang_id='de', value='Proxy Beta')
            with override('de'), CaptureQueriesContext(connection) as queries:
                item = QueryItemProxy.objects.get(pk=2)
                self.assertEqual(str(item.title), 'Proxy Beta')
                self.assertEqual(item.get_from_db()[910003]['de'].content_type_id, self.content_type.pk)
                self.assertEqual(self.ids(QueryItemProxy.objects.filter(title='proxy beta')), [2])
            self.assertEqual(len(queries), 2)
            with override('de'):
                item.title = 'Proxy changed'
                item.save()
                self.assertEqual(QueryItemProxy.objects.get(pk=2).title['de'], 'Proxy changed')
                self.assertEqual(QueryItem.objects.get(pk=2).title['de'], 'Beta')
        finally:
            descriptor.patch_unpatch('unpatch')

    def test_delete_and_string_aggregate_separator(self):
        self.assertEqual(self.ids(QueryItem.objects.filter(title__contains='Zulu\x1fAlpha')), [])
        QueryLink.objects.filter(item_id=3).delete()
        count = QueryItem.objects.filter(title='Gamma')._raw_delete(connection.alias)
        self.assertEqual(count, 1)
        self.assertEqual(self.ids(QueryItem.objects.all()), [1, 2, 4])

    def test_select_for_update_locks_original_tables(self):
        with override('de'), CaptureQueriesContext(connection) as queries:
            item = QueryItem.objects.select_for_update().get(pk=1)
            self.assertEqual(str(item.title), 'Zulu')
            link = QueryLink.objects.select_related('item').select_for_update().get(pk=1)
            self.assertEqual(str(link.item.title), 'Zulu')
            QueryLink.objects.select_related('item').select_for_update(of=('self',)).get(pk=1)
        self.assertIn('FOR UPDATE OF "tof_test_item"', queries[0]['sql'])
        self.assertIn('FOR UPDATE OF "tof_test_link", "tof_test_item"', queries[1]['sql'])
        self.assertTrue(queries[2]['sql'].endswith('FOR UPDATE OF "tof_test_link"'))

    def test_union_model_hydration_and_scalar_values(self):
        with override('de'), CaptureQueriesContext(connection) as queries:
            items = list(QueryItem.objects.filter(pk=1).union(QueryItem.objects.filter(pk=2)))
            self.assertEqual(sorted(str(item.title) for item in items), ['Beta', 'Zulu'])
        self.assertEqual(len(queries), 1)
        values = QueryItem.objects.filter(pk=1).values_list('title', flat=True).union(QueryItem.objects.filter(pk=2).values_list('title', flat=True))
        with override('de'):
            self.assertEqual(sorted(values), ['Beta', 'Zulu'])

    def test_original_query_class_and_backend_compiler_remain_intact(self):
        query.patch()
        compiler = QueryLink.objects.all().query.get_compiler(connection=connection)
        self.assertIsInstance(compiler, SQLCompiler)
        self.assertIs(type(QueryLink.objects.all().query), Query)
        sql, params = compiler.as_sql()
        self.assertNotIn('JOIN LATERAL', sql)
