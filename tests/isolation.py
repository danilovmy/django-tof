"""Keep DB-free UI tests independent of the database-backed TOF gettext hook."""
from unittest.mock import patch

from django.utils.translation.trans_real import DjangoTranslation

from tof.models import StaticMessageTranslation


class NativeTranslationsMixin:
    def _pre_setup(self):
        super()._pre_setup()
        # post_migrate installs TOF gettext for DB tests. These unit tests exercise
        # rendering/validation, not translation persistence, even in a full run.
        self.enterContext(patch.object(DjangoTranslation, 'gettext', StaticMessageTranslation.base_translator_cls))
        self.enterContext(patch.object(StaticMessageTranslation, 'CACHE', {}))
