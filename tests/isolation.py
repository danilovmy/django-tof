"""Keep DB-free UI tests independent of the database-backed TOF gettext hook."""
from contextlib import ExitStack
from unittest.mock import patch

from django.utils.translation.trans_real import DjangoTranslation

from tof.models import StaticMessageTranslation


class TestContextsMixin:
    def enter_context(self, context):
        stack = ExitStack()
        self.addCleanup(stack.close)
        return stack.enter_context(context)


class NativeTranslationsMixin(TestContextsMixin):
    def _pre_setup(self):
        super()._pre_setup()
        # post_migrate installs TOF gettext for DB tests. These unit tests exercise
        # rendering/validation, not translation persistence, even in a full run.
        self.enter_context(patch.object(DjangoTranslation, 'gettext', StaticMessageTranslation.base_translator_cls))
        self.enter_context(patch.object(StaticMessageTranslation, 'CACHE', {}))
