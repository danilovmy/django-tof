# This  classes sind Prototypes To add normal Translatable functionality to every Queryset function
# I want change SQL compiler method and change queryset on the end of queryset methods chain


class CompilerMixIn:

    def as_sql(self, *args, **kwargs):
        """here i want to change sql before"""
        print(args, kwargs)
        return super().as_sql(*args, **kwargs)


class QueryMixIn:
    """Represent a lazy database lookup for a set of objects."""

    def get_compiler(self, *args, **kwargs):
        compiler = super().get_compiler(*args, **kwargs)
        if not issubcalss(compiler, 'CompilerMixIn'):
            compiler.__class__.__bases__ = (CompilerMixIn, *compiler.__class__.__bases__)
        return compiler


class QuerySetMixIn:
    """Represent a lazy database lookup for a set of objects."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.patch_query()

    def patch_query(self):
        query = self.query
        if not issubcalss(query, 'QueryMixIn'):
            query.__class__.__bases__ = (QueryMixIn, *query.__class__.__bases__)
        return query
