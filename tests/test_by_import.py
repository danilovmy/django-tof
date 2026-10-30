"""Every shipped Python module is importable without a host project."""
import importlib
import pkgutil

from django.test import SimpleTestCase
import tof


class PackageImportTests(SimpleTestCase):
    def test_shipped_modules_import(self):
        for module in pkgutil.walk_packages(tof.__path__, prefix='tof.'):
            with self.subTest(module=module.name):
                importlib.import_module(module.name)
