import sys

from django.apps import AppConfig
from django.db import connection
from django.db.models.signals import post_migrate

from . import query


class TofConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tof'

    def ready(self):
        if {'test', 'migrate', 'makemigrations'}.intersection(set(sys.argv)):
            post_migrate.connect(self.patch, sender=self)
        else:
            self.ready_event, self.apps.ready_event = self.apps.ready_event, self

    def set(self):
        if not self.ready_event.is_set():
            with connection.temporary_connection():
                if 'tof_translatablefield' in connection.introspection.table_names():
                    self.patch()
            self.ready_event.set()

    def wait(self, *args, **kwargs):
        return self.ready_event.wait(*args, **kwargs)

    def is_set(self):
        return self.ready_event.is_set()

    def patch(self, *args, **kwargs):
        query.patch()
        self.models['translatablefield'].objects.patch_fields()
        self.models['staticmessagetranslation'].patch_djangotranslation()
        post_migrate.disconnect(self.patch, sender=self)
