"""Regression tests against the standalone package schema."""
import copy
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.contrib.postgres.aggregates import BoolOr, JSONBAgg, StringAgg
from django.core.exceptions import FieldError
from django.db import connection
from django.db.models import Count, F
from django.db.models.functions import Lower
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext
from django.utils.translation import override
from django.utils.translation.trans_real import DjangoTranslation

from tof.mixins import TofAdminMixin
from tof.models import StaticMessageTranslation, Translation
from tof.query import DisplayValue, TranslationCompilerMixin, _get_compiler

from . import test_query as fixture
from .fixtures import TranslationFixture

QueryItem = fixture.QueryItem
QueryLink = fixture.QueryLink


class CompilerRefactorTests(TranslationFixture):

    def test_default_order_uses_translations_for_models_and_values(self):
        with patch.object(QueryItem._meta, 'ordering', ('title',)), override('de'):
            with CaptureQueriesContext(connection) as queries:
                self.assertEqual([item.pk for item in QueryItem.objects.all()[:2]], [2, 3])
                self.assertEqual(list(QueryItem.objects.values_list('pk', flat=True)), [2, 3, 4, 1])
                self.assertEqual([row['pk'] for row in QueryItem.objects.values('pk', 'title')], [2, 3, 4, 1])
                self.assertEqual(list(QueryItem.objects.reverse().values_list('pk', flat=True)), [1, 4, 3, 2])
            self.assertEqual(len(queries), 4)
            self.assertTrue(all('ORDER BY COALESCE(' in row['sql'] for row in queries))
            self.assertEqual(str(QueryItem.objects.first().title), 'Beta')
            grouped = QueryItem.objects.annotate(total=Count('querylink')).query
            self.assertNotIn(' ORDER BY ', grouped.sql_with_params()[0].rsplit(' ON TRUE ', 1)[-1])

    def test_explicit_order_languages_expressions_reverse_and_slices(self):
        with patch.object(QueryItem._meta, 'ordering', ('title',)):
            for language, expected in [('de', [2, 3, 4, 1]), ('en', [1, 2, 3, 4])]:
                with self.subTest(language=language), override(language):
                    for ordering in [('title', 'pk'), (F('title').asc(), 'pk'), (Lower('title'), 'pk')]:
                        queryset = QueryItem.objects.order_by(*ordering)
                        self.assertEqual([item.pk for item in queryset], expected)
                        self.assertEqual(list(queryset.values_list('pk', flat=True)[1:3]), expected[1:3])
                    self.assertEqual(list(QueryItem.objects.order_by('-title', '-pk').values_list('pk', flat=True)), expected[::-1])
                    self.assertEqual(list(QueryItem.objects.order_by('title', 'pk').reverse().values_list('pk', flat=True)), expected[::-1])
                    self.assertEqual(list(QueryItem.objects.annotate(sort=Lower('title')).order_by(
                        '-sort').values_list('pk', flat=True)), expected[::-1])

    def test_display_value_keeps_language_values_in_parameter_order(self):
        compiler = QueryLink.objects.all().query.get_compiler(connection=connection)
        with patch('tof.query.TranslatableText.DEFAULT', "e'n"):
            sql, params = compiler.compile(DisplayValue(910001, "d'e"))
        self.assertEqual(tuple(params), ("d'e", "e'n"))
        self.assertIn('WHEN %s THEN 0 WHEN %s THEN 1 ELSE 2 END', sql)
        self.assertIn('"field_id" = 910001', sql)
        self.assertNotIn("d'e", sql)
        self.assertNotIn("e'n", sql)

    def test_related_default_order_expansion_uses_translations(self):
        with patch.object(QueryItem._meta, 'ordering', ('title',)), override('de'):
            default = QueryLink.objects.order_by('item').values_list('pk', flat=True)
            explicit = QueryLink.objects.order_by('item__title').values_list('pk', flat=True)
            self.assertEqual(list(default), [2, 3, 1])
            self.assertEqual(list(explicit), [2, 3, 1])
            self.assertIn('JOIN LATERAL', default.query.sql_with_params()[0])
            with patch.object(QueryLink._meta, 'ordering', ('item__title',)):
                self.assertEqual(list(QueryLink.objects.values_list('pk', flat=True)), [2, 3, 1])

    def changelist(self, params=None, ordering=('title',), per_page=100):
        class ItemAdmin(admin.ModelAdmin):
            actions = None
            list_display = ('id', 'display_title', 'number')
            show_full_result_count = False

            @admin.display(ordering='title')
            def display_title(self, obj):
                return obj.title

        ItemAdmin.ordering = ordering
        ItemAdmin.list_per_page = per_page
        model_admin = ItemAdmin(QueryItem, admin.AdminSite())
        TofAdminMixin.patch_bases(model_admin)
        request = RequestFactory().get('/admin/tof/queryitem/', params or {})
        request.user = SimpleNamespace(has_perm=lambda *args: True)
        changelist = model_admin.get_changelist_instance(request)
        self.assertIs(type(changelist), ChangeList)
        return changelist

    def test_actual_admin_default_selected_title_descending_and_reordering(self):
        with override('de'):
            default = self.changelist()
            selected = self.changelist({'o': '1'})
            descending = self.changelist({'o': '-1'})
            self.assertEqual([item.pk for item in default.result_list], [2, 3, 4, 1])
            self.assertEqual([item.pk for item in selected.result_list], [2, 3, 4, 1])
            self.assertEqual([item.pk for item in descending.result_list], [1, 4, 3, 2])
            default_sql = default.queryset.query.sql_with_params()[0]
            self.assertIn('ORDER BY COALESCE(', default_sql)
            self.assertIn('"tof_test_item"."id" DESC', default_sql)
            self.assertIn('ORDER BY COALESCE(', selected.queryset.query.sql_with_params()[0])
            self.assertEqual(list(default.queryset.order_by('title').values_list('pk', flat=True)), [2, 3, 4, 1])
            QueryItem.objects.filter(pk__in=[1, 2]).update(number=1)
            by_number = self.changelist({'o': '2'}, ordering=('title', 'description'))
            sql = by_number.queryset.query.sql_with_params()[0].split(' ORDER BY ')[-1]
            self.assertEqual(list(by_number.queryset.values_list('pk', flat=True)), [2, 1, 3, 4])
            self.assertIn('"tof_test_item"."number" ASC', sql)
            self.assertEqual(sql.count('COALESCE('), 2)

    def test_admin_meta_default_and_default_expression_ordering(self):
        with patch.object(QueryItem._meta, 'ordering', ('title',)), override('de'):
            self.assertEqual([item.pk for item in self.changelist(ordering=()).result_list], [2, 3, 4, 1])
        with override('de'):
            self.assertEqual([item.pk for item in self.changelist(ordering=(F('title').asc(),)).result_list], [2, 3, 4, 1])

    def test_custom_changelist_remains_native(self):
        class FilteredChangeList(ChangeList):
            def get_queryset(self, request):
                return super().get_queryset(request).filter(number__lte=2)

        class ChangeListAdmin(admin.ModelAdmin):
            def get_changelist(self, request, **kwargs):
                return FilteredChangeList

        class ItemAdmin(ChangeListAdmin):
            actions = None
            list_display = ('title',)
            ordering = ('title',)

        model_admin = ItemAdmin(QueryItem, admin.AdminSite())
        TofAdminMixin.patch_bases(model_admin)
        request = RequestFactory().get('/admin/tof/queryitem/', {'o': '0'})
        request.user = SimpleNamespace(has_perm=lambda *args: True)
        with override('de'):
            changelist = model_admin.get_changelist_instance(request)
            self.assertEqual([item.pk for item in changelist.result_list], [2, 1])
        self.assertIsInstance(changelist, FilteredChangeList)
        self.assertIs(type(changelist), model_admin.get_changelist(request))
        self.assertIs(type(changelist), FilteredChangeList)

    def test_admin_pages_use_translated_order_with_native_pk_tiebreaker(self):
        Translation.objects.create(content_type_id=self.content_type.pk, object_id=4, field_id=910001,
                                   lang_id='de', value='Beta')
        for language, expected in [('de', [4, 2, 3, 1]), ('en', [1, 4, 2, 3])]:
            with self.subTest(language=language), override(language), patch.object(
                    DjangoTranslation, 'gettext', StaticMessageTranslation.base_translator_cls):
                for page in (1, 2):
                    with CaptureQueriesContext(connection) as queries:
                        changelist = self.changelist({'p': str(page)}, per_page=2)
                        items = list(changelist.result_list)
                        self.assertEqual([item.pk for item in items], expected[(page - 1) * 2:page * 2])
                        self.assertTrue(all(str(item.title) for item in items))
                    self.assertEqual(len(queries), 2)

    def test_native_aggregates_bind_payload_search_display_predicate_params(self):
        queryset = QueryItem.objects.filter(title='zULu', description__contains='schreib').order_by('title')
        with override('de'):
            compiler = queryset.query.get_compiler(connection=connection)
            sql, params = compiler.as_sql()
            self.assertEqual([item.pk for item in queryset], [1])
            self.assertEqual(sql.count('JOIN LATERAL'), 1)
            self.assertIn('STRING_AGG', sql)
            self.assertIn('BOOL_OR', sql)
            plan = compiler._tof_plan
            (alias, content_type), item = next(iter(plan.aliases.items()))
            aggregate_query = plan.aggregate_query(alias, content_type, item)
            aggregates = aggregate_query.annotation_select.values()
            self.assertTrue(any(isinstance(value, JSONBAgg) for value in aggregates))
            self.assertTrue(any(isinstance(value, StringAgg) for value in aggregates))
            self.assertTrue(any(isinstance(value, BoolOr) for value in aggregates))
            self.assertEqual(_get_compiler(aggregate_query, connection=connection).as_sql()[1], params[:-3])
            self.assertIn('de', params)
            self.assertIn('en', params)
        with override('en'):
            self.assertEqual([item.pk for item in queryset.all()], [1])
            self.assertEqual(compiler.as_sql(), queryset.query.sql_with_params())

    def test_implicit_exact_stays_case_insensitive_only_for_translations(self):
        self.assertEqual(list(QueryItem.objects.filter(title='zULu').values_list('pk', flat=True)), [1])
        self.assertEqual(list(QueryItem.objects.filter(title__exact='zULu').values_list('pk', flat=True)), [])
        self.assertEqual(list(QueryItem.objects.filter(title='origin a').values_list('pk', flat=True)), [])
        self.assertIn('UPPER(', QueryItem.objects.filter(title='zULu').query.sql_with_params()[0])

    def test_real_backend_subclass_repeated_compile_and_source_isolation(self):
        query = QueryLink.objects.select_related('item').filter(item__title='zulu').order_by('item__title').query
        before = (copy.deepcopy(query.table_map), dict(query.alias_map), dict(query.annotations),
                  query.select, repr(query.where), dict(query.alias_refcount))
        compiler = query.get_compiler(connection=connection)
        self.assertIsInstance(compiler, type(_get_compiler(query, connection=connection)))
        self.assertIsInstance(compiler, TranslationCompilerMixin)
        self.assertIs(type(compiler), type(query.get_compiler(connection=connection)))
        with override('de'):
            first = compiler.as_sql()
            self.assertEqual(first, compiler.as_sql())
            self.assertEqual(list(QueryLink.objects.filter(item__title='zulu').values_list('pk', flat=True)), [1])
        with override('en'):
            self.assertNotEqual(first[1], compiler.as_sql()[1])
        self.assertEqual(before, (query.table_map, query.alias_map, query.annotations,
                                 query.select, repr(query.where), query.alias_refcount))
        self.assertFalse(hasattr(query, '_tof_plan'))

    def test_other_backends_keep_their_native_compiler(self):
        query = QueryLink.objects.all().query
        for vendor in ('mysql', 'sqlite'):
            with self.subTest(vendor=vendor):
                database = SimpleNamespace(vendor=vendor)
                native = SimpleNamespace(connection=database)
                with patch('tof.query._get_compiler', return_value=native):
                    self.assertIs(query.get_compiler(connection=database), native)

    def test_native_lock_flags_and_explicit_of_validation(self):
        with CaptureQueriesContext(connection) as queries:
            QueryItem.objects.select_for_update(of=('self',), nowait=True, no_key=True).get(pk=1)
            QueryItem.objects.select_for_update(skip_locked=True).get(pk=2)
        self.assertTrue(queries[0]['sql'].endswith('FOR NO KEY UPDATE OF "tof_test_item" NOWAIT'))
        self.assertTrue(queries[1]['sql'].endswith('FOR UPDATE OF "tof_test_item" SKIP LOCKED'))
        with self.assertRaises(FieldError):
            QueryItem.objects.select_for_update(of=('missing',)).get(pk=1)
