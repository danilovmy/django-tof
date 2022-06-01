# -*- coding: utf-8 -*-
import sys

from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.db import connection


class TofConfig(AppConfig):
    name = 'tof'
    __patched = False

    def ready(self):
        if {'test', 'migrate', 'makemigrations'}.intersection(set(sys.argv)):
            post_migrate.connect(self.patch, sender=self)
        elif 'tof_translatablefield' in connection.introspection.table_names():
            self.patch()

    def patch(self, *args, **kwargs):
        if not self.__patched:
            self.models['translatablefield'].objects.patch_fields()
            self.models['staticmessagetranslation'].patch_djangotranslation()
            self.__patched = True
