"""Independent PostgreSQL compiler checks using Django fixtures."""

from django.db import connection, models
from django.db.models import F, Q
from django.db.models.functions import Lower
from django.test.utils import CaptureQueriesContext
from django.utils.translation import override

from . import test_query as fixture
from .fixtures import TranslationFixture
from .models import VerificationPair
from tof.models import Translation

QueryItem = fixture.QueryItem


class IndependentCompilerTests(TranslationFixture):
    ids = fixture.QueryCompilerTests.ids

    def setUp(self):
        super().setUp()
        QueryItem.objects.bulk_create([
            QueryItem(pk=5, title='tie origin', description='tie source', number=5),
            QueryItem(pk=6, title='fallback origin', description='', number=6),
            QueryItem(pk=7, title='', description='', number=7),
            QueryItem(pk=8, title='Source only', description='', number=8),
        ])
        VerificationPair.objects.bulk_create([
            VerificationPair(pk=1, first_id=1, second_id=2), VerificationPair(pk=2, first_id=2, second_id=1),
            VerificationPair(pk=3, first_id=3, second_id=None),
        ])
        Translation.objects.bulk_create([
            Translation(content_type_id=self.content_type.pk, object_id=obj, field_id=field, lang_id=lang, value=value)
            for obj, field, lang, value in [
                (1, 910002, 'en', 'red'), (2, 910002, 'de', 'blue'),
                (3, 910002, 'de', 'red'), (5, 910001, 'de', 'Beta'),
                (5, 910001, 'en', 'Beta'), (5, 910002, 'de', 'red'),
                (6, 910001, 'fr', 'Delta'), (6, 910001, 'it', 'later'),
                (7, 910001, 'de', ''), (7, 910001, 'en', 'Echo'), (8, 910001, 'fr', ''),
            ]
        ])

    def test_multifield_and_nested_q_null_origin(self):
        with override('de'), CaptureQueriesContext(connection) as queries:
            self.assertEqual(self.ids(QueryItem.objects.filter(title__icontains='a', description='red')), [1, 3, 5])
            query = QueryItem.objects.filter(Q(title='gamma') | (Q(description='red') & ~Q(title='beta'))).exclude(title='zulu')
            self.assertEqual(self.ids(query), [3])
            self.assertEqual(self.ids(QueryItem.objects.exclude(Q(title='gamma') | Q(description='blue'))), [1, 4, 5, 6, 7, 8])
        self.assertEqual(len(queries), 3)
        self.assertTrue(all(q['sql'].count('JOIN LATERAL') == 1 for q in queries))

    def test_exact_and_physical_origin_case(self):
        self.assertEqual(self.ids(QueryItem.objects.filter(title='zUlU')), [1])
        self.assertEqual(self.ids(QueryItem.objects.filter(title__exact='zUlU')), [])
        self.assertEqual(self.ids(QueryItem.objects.filter(title='origin a')), [])
        self.assertEqual(self.ids(QueryItem.objects.filter(title__exact='Origin A')), [1])

    def test_contains_is_per_field_and_per_translation(self):
        self.assertEqual(self.ids(QueryItem.objects.filter(title__contains='ZuluAlpha')), [])
        self.assertEqual(self.ids(QueryItem.objects.filter(title__contains='Zulu\x1fAlpha')), [])
        self.assertEqual(self.ids(QueryItem.objects.filter(title__contains='red')), [])
        self.assertEqual(self.ids(QueryItem.objects.filter(description__contains='Zulu')), [])
        self.assertEqual(self.ids(QueryItem.objects.filter(title__icontains='AUTRE', description__icontains='RED')), [1])

    def test_order_both_languages_directions_ties_and_pagination(self):
        expected = {'de': [2, 5, 6, 7, 3, 4, 8, 1], 'en': [1, 2, 5, 6, 7, 3, 4, 8]}
        for lang, ids in expected.items():
            with self.subTest(lang=lang), override(lang), CaptureQueriesContext(connection) as queries:
                self.assertEqual(list(QueryItem.objects.order_by('title', 'pk').values_list('pk', flat=True)), ids)
                self.assertEqual(list(QueryItem.objects.order_by('-title', '-pk').values_list('pk', flat=True)), list(reversed(ids)))
                self.assertEqual([item.pk for item in QueryItem.objects.order_by('title', 'pk')[2:5]], ids[2:5])
            self.assertEqual(len(queries), 3)
            self.assertIn('LIMIT 3 OFFSET 2', queries[2]['sql'])

    def test_count_exists_and_pk_projection_sql(self):
        with CaptureQueriesContext(connection) as queries:
            qs = QueryItem.objects.filter(description='red')
            self.assertEqual(qs.count(), 3)
            self.assertTrue(qs.exists())
            self.assertFalse(qs.filter(title='nonexistent').exists())
            self.assertEqual(list(QueryItem.objects.order_by('pk').values_list('pk', flat=True)), list(range(1, 9)))
        self.assertEqual(len(queries), 4)
        self.assertTrue(all(q['sql'].count('JOIN LATERAL') == 1 for q in queries[:3]))
        self.assertNotIn('tof_translation', queries[3]['sql'])
        self.assertTrue(all('JSONB_AGG' not in q['sql'] for q in queries))

    def test_selected_fields_only_and_defer_reload(self):
        with CaptureQueriesContext(connection) as queries:
            item = QueryItem.objects.only('pk', 'title').get(pk=1)
            self.assertEqual(item.title['fr'], 'Autre')
            self.assertNotIn('description', item.__dict__)
        self.assertEqual(len(queries), 1)
        self.assertNotIn('910002', queries[0]['sql'])
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(item.description['en'], 'red')
            self.assertEqual(str(item.description), 'red')
        self.assertEqual(len(queries), 1)
        self.assertNotIn('910001', queries[0]['sql'])

    def test_two_aliases_and_nullable_related_hydration(self):
        with override('de'), CaptureQueriesContext(connection) as queries:
            pairs = list(VerificationPair.objects.select_related('first', 'second').order_by('pk'))
            self.assertEqual([(str(p.first.title), str(p.second.title) if p.second else None) for p in pairs], [('Zulu', 'Beta'), ('Beta', 'Zulu'), ('Gamma', None)])
            self.assertEqual(pairs[0].second.title['fr'], 'Autre')
        self.assertEqual(len(queries), 1)
        self.assertEqual(queries[0]['sql'].count('JOIN LATERAL'), 2)
        self.assertEqual(list(VerificationPair.objects.filter(first__title='zulu', second__title='beta').values_list('pk', flat=True)), [1])

    def test_one_query_map_and_language_switch_no_metadata_reads(self):
        query = QueryItem.objects.filter(description='red').order_by('title', 'pk').query
        original_where = repr(query.where)
        original_aliases = dict(query.alias_refcount)
        with CaptureQueriesContext(connection) as queries:
            with override('de'):
                first = query.sql_with_params()
                self.assertEqual(first, query.sql_with_params())
            with override('en'):
                self.assertNotEqual(first[1], query.sql_with_params()[1])
        self.assertEqual(len(queries), 0)
        self.assertEqual(repr(query.where), original_where)
        self.assertEqual(query.alias_refcount, original_aliases)
        with override('de'), CaptureQueriesContext(connection) as queries:
            items = list(QueryItem.objects.order_by('pk'))
            self.assertEqual([item.title['_origin'] for item in items], ['Origin A', 'Origin B', None, 'Only origin', 'tie origin', 'fallback origin', '', 'Source only'])
            self.assertEqual(items[0].title['en'], 'Alpha')
            self.assertEqual(str(items[5].title), 'Delta')
            self.assertEqual(items[0].get_from_db()[910001]['fr'].value, 'Autre')
        self.assertEqual(len(queries), 1)

    def test_expression_rhs_uses_individual_values(self):
        QueryItem.objects.filter(pk=1).update(description='Zulu')
        QueryItem.objects.filter(pk=2).update(description='Zulu\x1fAlpha')
        self.assertEqual(self.ids(QueryItem.objects.filter(title__contains=F('description'))), [1, 4, 6, 7, 8])

    def test_related_expression_rhs_uses_existing_alias(self):
        # Translation on one alias is compared with the physical RHS field,
        # matching the established original-column OR any-translation rule.
        QueryItem.objects.filter(pk=2).update(description='Zulu')
        self.assertEqual(list(VerificationPair.objects.filter(first__title__exact=F('second__description')).values_list('pk', flat=True)), [1])

    def test_lower_transform_lookup_uses_displayed_text(self):
        models.CharField.register_lookup(Lower)
        try:
            with override('de'):
                self.assertEqual(self.ids(QueryItem.objects.filter(title__lower='zulu')), [1])
                self.assertEqual(self.ids(QueryItem.objects.filter(title__lower='alpha')), [])
        finally:
            models.CharField._unregister_lookup(Lower)

    def test_distinct_on_translated_title(self):
        with override('de'), CaptureQueriesContext(connection) as queries:
            rows = list(QueryItem.objects.order_by('title', 'pk').distinct('title').values_list('title', flat=True))
            items = list(QueryItem.objects.order_by('title', 'pk').distinct('title'))
        self.assertEqual(rows, ['Beta', 'Delta', 'Echo', 'Gamma', 'Only origin', 'Source only', 'Zulu'])
        self.assertEqual([item.pk for item in items], [2, 6, 7, 3, 4, 8, 1])
        self.assertEqual(len(queries), 2)
        self.assertTrue(all('DISTINCT ON (COALESCE(' in q['sql'] for q in queries))

    def test_union_model_order_uses_displayed_text(self):
        with override('de'), CaptureQueriesContext(connection) as queries:
            qs = QueryItem.objects.filter(pk__in=[1, 3]).union(QueryItem.objects.filter(pk__in=[2, 5]))
            items = list(qs.order_by('title', 'pk')[1:3])
        self.assertEqual([item.pk for item in items], [5, 3])
        self.assertEqual(len(queries), 1)
        self.assertIn('ORDER BY "__orderbycol1" ASC, "col1" ASC LIMIT 2 OFFSET 1', queries[0]['sql'])

    def test_union_scalar_order_count_and_exists(self):
        with override('de'), CaptureQueriesContext(connection) as queries:
            qs = QueryItem.objects.filter(pk__in=[1, 3]).values_list('title', flat=True).union(QueryItem.objects.filter(pk__in=[2, 5]).values_list('title', flat=True))
            self.assertEqual(list(qs.order_by('title')), ['Beta', 'Gamma', 'Zulu'])
            self.assertEqual(qs.count(), 3)
            self.assertTrue(qs.exists())
        self.assertEqual(len(queries), 3)
        self.assertTrue(all('JSONB_AGG' not in q['sql'] for q in queries))

    def test_save_fresh_eav_and_origin_isolation(self):
        with override('de'):
            item = QueryItem.objects.get(pk=1)
            Translation.objects.filter(object_id=1, field_id=910001, lang_id='de').update(value='externally changed')
            item.title = 'Saved now'
            with CaptureQueriesContext(connection) as queries:
                item.save(update_fields=['title'])
            self.assertTrue(any('SELECT' in q['sql'] and '"tof_translation"' in q['sql'] for q in queries))
            self.assertEqual(QueryItem.objects.get(pk=1).title['_origin'], 'Origin A')
            self.assertEqual(Translation.objects.get(object_id=1, field_id=910001, lang_id='de').value, 'Saved now')
            self.assertEqual(item.title['_origin'], 'Origin A')
            self.assertFalse(item.title._tof_saved['de']._state.adding)
