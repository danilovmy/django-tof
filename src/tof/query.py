"""Late PostgreSQL translations on the selected Django backend compiler."""
import json

from django.contrib.postgres.aggregates import BoolOr, JSONBAgg, StringAgg
from django.core.exceptions import EmptyResultSet, FullResultSet
from django.db.models import Func, JSONField, Max, Q, Subquery, TextField, Value
from django.db.models.expressions import Col, Expression
from django.db.models.functions import Cast, Coalesce
from django.db.models.lookups import Lookup
from django.db.models.sql.query import Query
from django.utils.hashable import make_hashable

from .utils import TranslatableText, tof_class

_get_compiler = Query.get_compiler
_build_lookup = Query.build_lookup


def translated_field(compiler, col):
    if not isinstance(col, Col):
        return None
    model = col.target.model
    query = compiler.query
    if col.alias == query.base_table and query.model._meta.concrete_model == model._meta.concrete_model:
        model = query.model
    else:
        join = query.alias_map.get(col.alias)
        related = getattr(getattr(join, 'join_field', None), 'related_model', None)
        if related and related._meta.concrete_model == model._meta.concrete_model:
            model = related
    descriptor = getattr(model, col.target.name, None)
    return descriptor if getattr(descriptor, 'replaced_field', None) else None


class TranslatedSelect(Col):
    """Only direct result columns carry maps; nested expressions remain text."""
    def __init__(self, col, descriptor, sql, params):
        super().__init__(col.alias, col.target, col.output_field)
        self.col, self.descriptor, self.sql, self.params = col, descriptor, sql, params

    def as_sql(self, compiler, connection):
        return self.sql, self.params

    def get_group_by_cols(self):
        return [self.col]

    def get_db_converters(self, connection):
        return [self.convert]

    def convert(self, value, expression, connection):
        from .models import Translation
        origin, rows = json.loads(value) if isinstance(value, str) else value
        result = TranslatableText().update(_origin=origin)
        vars(result)['_origin'] = origin
        saved = {}
        for pk, object_id, lang, text in rows or ():
            translation = Translation(id=pk, object_id=object_id, field_id=self.descriptor.pk,
                                      content_type_id=self.descriptor.translation_content_type_id, lang_id=lang, value=text)
            translation._state.adding, translation._state.db = False, connection.alias
            saved[lang] = translation
            result[lang] = text
        vars(result)['_tof_saved'] = saved
        return result


class TranslationPlan:
    def __init__(self, compiler, backend_compile):
        self.compiler, self.backend_compile = compiler, backend_compile
        self.aliases = {}
        self.scope = compiler.query.alias_prefix
        self.physical = False
        self.predicates = {}
        self.language = TranslatableText.get_lang()

    def field(self, col, descriptor, kind=None):
        key = col.alias, descriptor.translation_content_type_id
        if key not in self.aliases:
            self.aliases[key] = {'name': f'__tof_{self.scope}_{len(self.aliases)}', 'fields': {}, 'uses': {}, 'matches': {}}
        item = self.aliases[key]
        item['fields'][descriptor.pk] = descriptor
        if kind:
            item['uses'].setdefault(descriptor.pk, set()).add(kind)
        return item

    def column(self, item, kind, field_id):
        quote = self.compiler.connection.ops.quote_name
        return f'{quote(item["name"])}.{quote(f"{kind}_{field_id}")}'

    def origin(self, node):
        previous, self.physical = self.physical, True
        try:
            return self.backend_compile(node)
        finally:
            self.physical = previous

    def compile(self, compiler, node):
        compiled = self.predicates.get(id(node))
        if compiled is not None:
            return compiled
        if isinstance(node, TranslatedSelect):
            return self.backend_compile(node)
        if not self.physical and isinstance(node, Lookup):
            descriptor = translated_field(compiler, node.lhs)
            if descriptor:
                item = self.field(node.lhs, descriptor)
                origin_sql, origin_params = self.origin(node)
                if node.lookup_name in ('contains', 'icontains') and isinstance(node.rhs, str) and '\x1f' not in node.rhs:
                    item['uses'].setdefault(descriptor.pk, set()).add('search_text')
                    lookup = node.copy()
                    lookup.lhs = AggregateColumn(self.column(item, 'search_text', descriptor.pk), node.lhs.output_field)
                    translated_sql, translated_params = self.backend_compile(lookup)
                    return f'(COALESCE({origin_sql}, FALSE) OR COALESCE({translated_sql}, FALSE))', (*origin_params, *translated_params)
                # Evaluate conventional lookups per value inside the existing aggregate.
                # This also handles expression/subquery RHS without flattening exact/in semantics.
                lookup = node.copy()
                from .models import Translation
                lookup.lhs = Col('__tof_value', Translation._meta.get_field('value'))
                if getattr(node, '_tof_implicit_exact', False):
                    lookup = lookup.lhs.get_lookup('iexact')(lookup.lhs, lookup.rhs)
                translated_sql, translated_params = self.origin(lookup)
                key = descriptor.pk, translated_sql, make_hashable(translated_params)
                if key not in item['matches']:
                    item['matches'][key] = (f'matches_{len(item["matches"])}', lookup)
                name = item['matches'][key][0]
                match = f'{compiler.connection.ops.quote_name(item["name"])}.{compiler.connection.ops.quote_name(name)}'
                return f'(COALESCE({origin_sql}, FALSE) OR COALESCE({match}, FALSE))', origin_params
        if not self.physical:
            descriptor = translated_field(compiler, node)
            if descriptor:
                item = self.field(node, descriptor, 'display_value')
                return self.origin(Coalesce(
                    AggregateColumn(self.column(item, "display_value", descriptor.pk), node.output_field), node))
        return self.backend_compile(node)

    def aggregate_query(self, alias, content_type, item):
        from .models import Translation
        query = Query(Translation)
        query.change_aliases({query.get_initial_alias(): '__tof_value'})
        query.external_aliases = {name: name not in self.compiler.query.table_map
                                  for name in self.compiler.query.alias_map}
        query.default_cols = False
        query.clear_ordering(force=True)
        model = next(iter(item['fields'].values())).replaced_field.field.model
        query.add_q(Q(content_type_id=content_type, object_id=Col(alias, model._meta.pk),
                      field_id__in=list(item['fields'])))
        for field_id in item['fields']:
            condition = Q(field_id=field_id)
            uses = item['uses'].get(field_id, ())
            if 'payload' in uses:
                rows = Func('id', 'object_id', 'lang_id', 'value',
                            function='JSONB_BUILD_ARRAY', output_field=JSONField())
                query.add_annotation(JSONBAgg(rows, ordering='id', filter=condition, default=None), f'payload_{field_id}')
            if 'search_text' in uses:
                query.add_annotation(StringAgg('value', '\x1f', ordering='id', filter=condition, default=None), f'search_text_{field_id}')
            if 'display_value' in uses:
                query.add_annotation(DisplayValue(field_id, self.language), f'display_value_{field_id}')
        for (field_id, _, _), (name, lookup) in item['matches'].items():
            query.add_annotation(BoolOr(lookup, filter=Q(field_id=field_id)), name)
        return query

    def joins(self):
        compiler = self.compiler
        quote = compiler.connection.ops.quote_name
        result, params = [], []
        for (alias, content_type), item in self.aliases.items():
            query = self.aggregate_query(alias, content_type, item)
            sql, query_params = _get_compiler(query, connection=compiler.connection).as_sql()
            result.append(f'LEFT JOIN LATERAL ({sql}) {quote(item["name"])} ON TRUE')
            params.extend(query_params)
        return result, params


class DisplayValue(Func):
    """Django 4.2's ordered ArrayAgg binds FILTER params before ORDER BY params."""
    template = (
        '(ARRAY_AGG(NULLIF("__tof_value"."value", \'\') ORDER BY CASE "__tof_value"."lang_id" '
        'WHEN %(expressions)s THEN 1 ELSE 2 END, "__tof_value"."id") '
        'FILTER (WHERE "__tof_value"."field_id" = %(field_id)s '
        'AND "__tof_value"."value" <> \'\'))[1]'
    )
    arg_joiner = ' THEN 0 WHEN '

    def __init__(self, field_id, language):
        super().__init__(Value(language), Value(TranslatableText.DEFAULT), field_id=int(field_id), output_field=TextField())


class AggregateColumn(Expression):
    def __init__(self, sql, output_field):
        super().__init__(output_field=output_field)
        self.sql = sql

    def as_sql(self, compiler, connection):
        return self.sql, ()


def model_columns(info):
    if info:
        yield from info['select_fields']
        for related in info.get('related_klass_infos', ()):
            yield from model_columns(related)


class TranslationCompilerMixin:
    def as_sql(self, *args, **kwargs):
        self.query = self.source_query.clone()
        self.query.table_map = {table: aliases[:] for table, aliases in self.query.table_map.items()}
        self.quote_cache = {'*': '*'}
        self._tof_plan = TranslationPlan(self, super().compile)
        return super().as_sql(*args, **kwargs)

    def compile(self, node):
        plan = getattr(self, '_tof_plan', None)
        if plan is None:
            return super().compile(node)
        return plan.compile(self, node)

    def get_select(self, *args, **kwargs):
        select, klass_info, annotations = super().get_select(*args, **kwargs)
        if self.query.subquery or not self.query.default_cols:
            return select, klass_info, annotations
        plan = self._tof_plan
        columns = set(model_columns(klass_info))
        hydrated = []
        for index, (expression, (sql, params), alias) in enumerate(select):
            descriptor = translated_field(self, expression) if index in columns else None
            if descriptor:
                item = plan.field(expression, descriptor, 'payload')
                payload = AggregateColumn(plan.column(item, 'payload', descriptor.pk), JSONField())
                if self.query.group_by is not None:
                    payload = Cast(Max(Cast(payload, TextField())), JSONField())
                sql, params = plan.origin(Func(expression, payload, function='JSONB_BUILD_ARRAY', output_field=JSONField()))
                expression = TranslatedSelect(expression, descriptor, sql, params)
            hydrated.append((expression, (sql, params), alias))
        return hydrated, klass_info, annotations

    def get_from_clause(self):
        # Django compiles WHERE after FROM, so discover filter-only fields first.
        for node in (self.where, self.having):
            if node is not None:
                try:
                    self._tof_plan.predicates[id(node)] = self.compile(node)
                except (EmptyResultSet, FullResultSet):
                    pass
        result, params = super().get_from_clause()
        joins, join_params = self._tof_plan.joins()
        return [*result, *joins], [*params, *join_params]

    def get_select_for_update_of_arguments(self):
        if self._tof_plan.aliases and not self.query.select_for_update_of:
            # Lock the original tables, excluding the aggregate's nullable side.
            return [self.quote_name_unless_alias(alias) for alias in self.query.alias_map if self.query.alias_refcount[alias]]
        return super().get_select_for_update_of_arguments()

    def collapse_group_by(self, expressions, having):
        result = super().collapse_group_by(expressions, having)
        # PostgreSQL cannot infer dependence of a LATERAL result on the base PK.
        for expression in expressions:
            if translated_field(self, expression) and expression not in result:
                result.append(expression)
        return result


class TranslationWriteCompilerMixin:
    def as_sql(self, *args, **kwargs):
        query = self.source_query
        self.query = query.clone()
        self.query.table_map = {table: aliases[:] for table, aliases in self.query.table_map.items()}
        if any(translated_field(self, col) for col in query._gen_cols([query.where])):
            source = query.chain(Query)
            source.clear_select_clause()
            source.add_fields([query.model._meta.pk.name])
            source.clear_ordering(force=True)
            source.subquery = True
            self.query.where = self.query.build_filter((f'{query.model._meta.pk.name}__in', Subquery(source)))[0]
        return super().as_sql(*args, **kwargs)


def get_compiler(query, *args, **kwargs):
    backend = _get_compiler(query, *args, **kwargs)
    if backend.connection.vendor != 'postgresql':
        return backend
    if query.compiler == 'SQLCompiler':
        mixin = TranslationCompilerMixin
    elif query.compiler in ('SQLUpdateCompiler', 'SQLDeleteCompiler'):
        mixin = TranslationWriteCompilerMixin
    else:
        return backend
    compiler = tof_class(type(backend), mixin)(query, backend.connection, backend.using, backend.elide_empty)
    compiler.source_query = query
    return compiler


def patch():
    Query.get_compiler = get_compiler
    Query.build_lookup = build_lookup


def build_lookup(query, lookups, lhs, rhs):
    lookup = _build_lookup(query, lookups, lhs, rhs)
    if not lookups and lookup is not None and lookup.lookup_name == 'exact':
        lookup._tof_implicit_exact = True
    return lookup
