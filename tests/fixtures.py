"""Tests use the package migrations and Django fixtures, never a project database."""
from unittest import skipUnless

from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import TestCase

from tof import query
from tof.models import TranslatableField
from .isolation import NativeTranslationsMixin
from .models import QueryItem


@skipUnless(connection.vendor == 'postgresql', 'Translation compiler requires PostgreSQL')
class TranslationFixture(NativeTranslationsMixin, TestCase):
    fixtures = ['regression']

    def setUp(self):
        super().setUp()
        query.patch()
        ContentType.objects.clear_cache()
        self.content_type = ContentType.objects.get_for_model(QueryItem)
        self.descriptors = list(TranslatableField.objects.filter(pk__in=[910001, 910002]))
        for descriptor in self.descriptors:
            descriptor.patch_unpatch('patch')

    def tearDown(self):
        for descriptor in reversed(self.descriptors):
            descriptor.patch_unpatch('unpatch')
        ContentType.objects.clear_cache()
        super().tearDown()
