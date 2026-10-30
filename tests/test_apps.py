import sys
from threading import Event
from contextlib import nullcontext
from unittest.mock import Mock, patch

from django.apps import AppConfig
from django.apps.registry import Apps
from django.dispatch import Signal
from django.test import SimpleTestCase

import tof
import tests
from tof.apps import TofConfig
from .isolation import TestContextsMixin


class StartupTests(TestContextsMixin, SimpleTestCase):
    def setUp(self):
        self.events = []
        self.config = TofConfig('tof', tof)
        self.config.import_models = Mock()
        self.config.patch = Mock(side_effect=lambda: self.events.append('patch'))
        self.last = AppConfig('tests', tests)
        self.last.import_models = Mock()
        self.last.ready = Mock(side_effect=lambda: self.events.append('last ready'))
        self.query_patch = self.enter_context(patch('tof.apps.query.patch'))
        self.connection = self.enter_context(patch('tof.apps.connection'))
        self.connection.temporary_connection.return_value = nullcontext()
        self.connection.introspection.table_names.side_effect = self.read_tables
        self.enter_context(patch.object(sys, 'argv', ['manage.py', 'check']))

    def read_tables(self):
        self.assertTrue(self.config.apps.ready)
        self.assertFalse(self.config.apps.ready_event.is_set())
        self.events.append('read')
        return ['tof_translatablefield']

    def test_patch_runs_after_all_ready_before_event_is_set_and_only_once(self):
        def last_ready():
            self.assertIs(self.config.apps.ready_event, self.config)
            self.assertFalse(self.config.apps.ready_event.is_set())
            self.assertFalse(self.config.apps.ready_event.wait(timeout=0))
            self.events.append('last ready')

        self.last.ready.side_effect = last_ready
        registry = Apps([self.config, self.last])
        self.assertEqual(self.events, ['last ready', 'read', 'patch'])
        self.assertIs(registry.ready_event, self.config)
        self.assertTrue(registry.ready_event.is_set())
        self.assertTrue(self.config.wait(0))
        self.assertTrue(self.config.is_set())
        registry.ready_event.set()
        self.config.patch.assert_called_once_with()
        self.connection.introspection.table_names.assert_called_once_with()
        self.connection.temporary_connection.assert_called_once_with()

    def test_missing_table_still_sets_event_without_patching(self):
        self.connection.introspection.table_names.side_effect = None
        self.connection.introspection.table_names.return_value = []
        registry = Apps([self.config, self.last])
        self.assertTrue(registry.ready_event.is_set())
        registry.ready_event.set()
        self.config.patch.assert_not_called()
        self.connection.introspection.table_names.assert_called_once_with()
        self.connection.temporary_connection.assert_called_once_with()

    def test_event_with_readonly_methods_is_supported(self):
        class SlottedEvent:
            __slots__ = ('_event',)

            def __init__(self):
                self._event = Event()

            def __getattr__(self, name):
                return getattr(self._event, name)

            def set(self):
                self._event.set()

        with patch('django.apps.registry.threading.Event', SlottedEvent):
            registry = Apps([self.config, self.last])
        self.assertIs(registry.ready_event, self.config)
        self.assertIs(type(self.config.ready_event), SlottedEvent)
        self.assertTrue(registry.ready_event.is_set())
        self.assertEqual(self.events, ['last ready', 'read', 'patch'])

    def test_patch_error_aborts_startup_without_setting_event(self):
        self.config.patch.side_effect = RuntimeError('patch failed')
        with self.assertRaisesMessage(RuntimeError, 'patch failed'):
            Apps([self.config, self.last])
        event = self.config.apps.ready_event
        self.assertIs(event, self.config)
        self.assertFalse(event.is_set())

    def test_failed_startup_can_retry_before_setting_original_event(self):
        self.config.patch.side_effect = [RuntimeError('patch failed'), None]
        with self.assertRaisesMessage(RuntimeError, 'patch failed'):
            Apps([self.config, self.last])
        event = self.config.apps.ready_event
        self.assertFalse(event.is_set())
        event.set()
        self.assertTrue(event.is_set())
        self.assertEqual(self.config.patch.call_count, 2)
        self.assertEqual(self.connection.introspection.table_names.call_count, 2)
        event.set()
        self.assertEqual(self.connection.introspection.table_names.call_count, 2)

    def test_database_management_commands_keep_post_migrate_initialization(self):
        for command in ('test', 'migrate', 'makemigrations'):
            with self.subTest(command=command), patch.object(sys, 'argv', ['manage.py', command]), patch(
                    'tof.apps.post_migrate') as signal:
                registry = Apps([self.config, self.last])
                signal.connect.assert_called_once_with(self.config.patch, sender=self.config)
                self.assertIs(registry.ready_event.set.__func__, type(registry.ready_event).set)
                self.assertTrue(registry.ready_event.is_set())
        self.connection.introspection.table_names.assert_not_called()
        self.config.patch.assert_not_called()
        self.query_patch.assert_not_called()

    def test_post_migrate_retries_failed_patch_then_disconnects(self):
        del self.config.patch
        fields, messages = Mock(), Mock()
        self.config.models = {'translatablefield': fields, 'staticmessagetranslation': messages}
        messages.patch_djangotranslation.side_effect = [RuntimeError('patch failed'), None]
        signal = Signal()
        with patch.object(sys, 'argv', ['manage.py', 'test']), patch('tof.apps.post_migrate', signal):
            registry = Apps([self.config, self.last])
            self.assertTrue(registry.ready_event.is_set())
            self.query_patch.assert_not_called()
            with self.assertRaisesMessage(RuntimeError, 'patch failed'):
                signal.send(sender=self.config, using='default')
            self.assertTrue(signal.has_listeners(self.config))
            signal.send(sender=self.config, using='default')
            self.assertFalse(signal.has_listeners(self.config))
            signal.send(sender=self.config, using='logs')
        self.assertEqual(fields.objects.patch_fields.call_count, 2)
        self.assertEqual(messages.patch_djangotranslation.call_count, 2)
        self.assertEqual(self.query_patch.call_count, 2)
