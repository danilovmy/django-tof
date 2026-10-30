import unittest
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils.translation.trans_real import DjangoTranslation

from tof.models import StaticMessageTranslation
from .isolation import NativeTranslationsMixin


class NativeTranslationsIsolationTests(SimpleTestCase):
    def test_hook_and_cache_are_restored_even_when_a_unit_test_fails(self):
        cache = {'existing': object()}

        def database_gettext(translator, message):
            raise AssertionError('A DB-free test reached the database translation hook')

        class RenderingTest(NativeTranslationsMixin, SimpleTestCase):
            def runTest(self):
                self.assertEqual(DjangoTranslation('en').gettext('Hello'), 'Hello')
                StaticMessageTranslation.CACHE['temporary'] = object()
                self.fail('Exercise cleanup after a failed assertion')

        with patch.object(DjangoTranslation, 'gettext', database_gettext), patch.object(StaticMessageTranslation, 'CACHE', cache):
            result = unittest.TestResult()
            RenderingTest().run(result)

            self.assertEqual(len(result.failures), 1)
            self.assertEqual(result.errors, [])
            self.assertIs(DjangoTranslation.gettext, database_gettext)
            self.assertIs(StaticMessageTranslation.CACHE, cache)
            self.assertEqual(set(cache), {'existing'})
