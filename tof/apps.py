import sys

from django.apps import AppConfig, apps
from django.db import connection
from django.db.models.signals import post_migrate


class TofConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tof'
    __patched = False

    def ready(self):
        if {'test', 'migrate', 'makemigrations'}.intersection(set(sys.argv)):
            return post_migrate.connect(self.release, sender=self)
        return apps.ready_event._cond._waiters.append(self)

    def release(self, *args, **kwargs):
        if not self.__patched:
            if 'tof_translatablefield' in connection.introspection.table_names():
                self.models['translatablefield'].objects.patch_fields()
                self.models['staticmessagetranslation'].patch_djangotranslation()
                self.__patched = True
