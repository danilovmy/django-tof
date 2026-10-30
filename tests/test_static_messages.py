from unittest.mock import patch

from django.test import TestCase
from django.utils.translation import override
from django.utils.translation.trans_real import DjangoTranslation

from tof.models import StaticMessageTranslation
from .isolation import NativeTranslationsMixin


class StaticMessageTranslationTests(NativeTranslationsMixin, TestCase):
    def test_gettext_saves_and_caches_fallback_for_new_message(self):
        message = 'TOF first fallback regression'
        with override('de'), patch.object(StaticMessageTranslation, 'base_translator_cls', return_value='Automatic fallback'):
            self.assertEqual(StaticMessageTranslation.gettext(DjangoTranslation('de'), message), 'Automatic fallback')
            cached = StaticMessageTranslation.CACHE[message]
            self.assertEqual(cached.translations.get(lang_id='de').value, 'Automatic fallback')
            with self.assertNumQueries(0):
                self.assertEqual(StaticMessageTranslation.gettext(DjangoTranslation('de'), message), 'Automatic fallback')

    def test_stale_cache_preserves_translation_saved_by_another_request(self):
        message = 'TOF concurrent fallback regression'
        with override('de'):
            cached = StaticMessageTranslation.objects.create(message=message)
            cached.refresh_from_db()
            self.assertFalse(cached.translation.current)
            cached.translations.create(field=StaticMessageTranslation.translation, lang_id='de', value='Manual translation')
            with patch.object(StaticMessageTranslation, 'base_translator_cls', return_value='Automatic fallback'):
                self.assertEqual(StaticMessageTranslation.gettext(DjangoTranslation('de'), message), 'Manual translation')
            self.assertEqual(list(cached.translations.values_list('value', flat=True)), ['Manual translation'])
