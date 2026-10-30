from types import SimpleNamespace
from unittest.mock import patch

from django import forms
from django.contrib import admin
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from tof.fields import TranslatableFieldFormField
from tof.mixins import TofAdminMixin
from tof.models import StaticMessageTranslation
from tof.utils import TranslatableText
from tof.views import ActionView
from tof.widgets import TranslatableFieldHiddenWidget
from .isolation import NativeTranslationsMixin
from .models import QueryItem, QueryLink


class AdminActionTests(NativeTranslationsMixin, SimpleTestCase):
    def test_confirmation_and_submission_use_package_templates(self):
        class ConfirmAction(ActionView):
            short_description = 'Standalone action'
            description = 'Confirm using package templates.'
            allow_empty = True

            def processing(self, *args, **kwargs):
                return HttpResponse('processed')

        factory = RequestFactory()
        user = SimpleNamespace(
            is_active=True, is_staff=True, is_superuser=True,
            has_perm=lambda *args: True, has_perms=lambda *args: True,
            has_module_perms=lambda *args: True,
        )
        model_admin = admin.site._registry[StaticMessageTranslation]
        action = ConfirmAction.as_view()
        request = factory.get('/admin/tof/staticmessagetranslation/')
        request.user = user
        response = action(model_admin, request, StaticMessageTranslation.objects.none())
        response.render()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirm using package templates.')
        self.assertContains(response, 'name="YesNoForm-answer"')
        self.assertContains(response, 'value="yes"')
        request = factory.post('/admin/tof/staticmessagetranslation/', {'YesNoForm-answer': 'yes'})
        request.user = user
        response = action(model_admin, request, StaticMessageTranslation.objects.none())
        self.assertEqual(response.content, b'processed')
        self.assertIn('Standalone action', ConfirmAction.render_as_button())

    def test_plain_and_shared_admin_classes_are_patched_per_registration(self):
        class SharedAdmin(admin.ModelAdmin):
            pass

        for admin_class in (admin.ModelAdmin, SharedAdmin):
            with self.subTest(admin_class=admin_class.__name__):
                selected, untouched = admin.AdminSite(), admin.AdminSite()
                for site in (selected, untouched):
                    site.register(QueryItem, admin_class)
                    site.register(QueryLink, admin_class)
                original_bases = admin_class.__bases__
                try:
                    # Patch only the selected registrations. Sharing the original
                    # admin class must not spread translation behavior.
                    first, second = selected._registry[QueryItem], selected._registry[QueryLink]
                    TofAdminMixin.patch_bases(first)
                    TofAdminMixin.patch_bases(second)
                    self.assertEqual(admin_class.__bases__, original_bases)
                    self.assertIsInstance(first, TofAdminMixin)
                    self.assertIsInstance(second, TofAdminMixin)
                    self.assertNotIsInstance(untouched._registry[QueryItem], TofAdminMixin)
                    TofAdminMixin.unpatch_bases(first, {})
                    self.assertNotIsInstance(first, TofAdminMixin)
                    self.assertIsInstance(second, TofAdminMixin)
                finally:
                    TofAdminMixin.unpatch_bases(selected._registry[QueryItem], {})
                    TofAdminMixin.unpatch_bases(selected._registry[QueryLink], {})
                    for site in (selected, untouched):
                        site.unregister(QueryItem)
                        site.unregister(QueryLink)

    def test_hidden_translation_widget_and_bound_field_render(self):
        value = TranslatableText().update(_origin='Origin', de='Hallo', en='Hello')
        with patch('tof.widgets.resolve_admin_link', return_value=None):
            widget = TranslatableFieldHiddenWidget(attrs={'id': 'id_hidden'})
            self.assertTrue(widget.is_hidden)
            html = widget.render('title', value)
            self.assertIn('type="hidden"', html)
            self.assertIn('name="title_de"', html)

            class Form(forms.Form):
                title = TranslatableFieldFormField((forms.CharField(),), initial=value)

            html = Form()['title'].as_hidden()
            self.assertIn('type="hidden"', html)
            self.assertIn('name="title_en"', html)
