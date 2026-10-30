import copy
from unittest.mock import patch

from unittest import skipUnless

try:
    from ckeditor.widgets import CKEditorWidget
    from ckeditor_uploader.widgets import CKEditorUploadingWidget
except ImportError:
    CKEditorWidget = CKEditorUploadingWidget = None
from django import forms
from django.contrib.admin.widgets import AdminTextareaWidget, AdminTextInputWidget
from django.test import SimpleTestCase

from tof.fields import TranslatableFieldFormField
from tof.utils import TranslatableText
from tof.widgets import TranslatableFieldWidget, ValueFormatterMixin
from .isolation import NativeTranslationsMixin


class TranslationWidgetTests(NativeTranslationsMixin, SimpleTestCase):
    def setUp(self):
        self.enterContext(patch('tof.widgets.resolve_admin_link', return_value=None))

    def context(self, widget):
        return widget.get_context('title', [('de', 'Hallo')], {'id': 'id_title'})

    def test_construction_leaves_widget_and_its_class_unchanged(self):
        native = forms.TextInput()
        original = forms.TextInput.__bases__, forms.TextInput.__mro__
        widget = TranslatableFieldWidget([native])
        self.assertIs(widget.widgets[0], native)
        self.assertIs(type(native), forms.TextInput)
        self.assertNotIsInstance(native, ValueFormatterMixin)
        self.assertEqual((forms.TextInput.__bases__, forms.TextInput.__mro__), original)

    def check_widget_order(self, classes):
        originals = {cls: (cls.__bases__, cls.__mro__) for cls in classes}
        untouched_widgets = []
        for cls in classes:
            native, untouched = cls(), cls()
            untouched_widgets.append(untouched)
            widget = TranslatableFieldWidget([native])
            self.context(widget)
            self.assertIsInstance(native, cls)
            self.assertIsInstance(native, ValueFormatterMixin)
            self.assertEqual(native.format_value(('de', 'Hallo')), ['de', 'Hallo'])
        for untouched in untouched_widgets:
            self.assertNotIsInstance(untouched, ValueFormatterMixin)
        for cls, original in originals.items():
            self.assertEqual((cls.__bases__, cls.__mro__), original)

    def test_admin_before_text_input_patches_only_rendered_instances(self):
        self.check_widget_order((AdminTextInputWidget, forms.TextInput))

    def test_text_input_before_admin_patches_only_rendered_instances(self):
        self.check_widget_order((forms.TextInput, AdminTextInputWidget))

    def test_repeated_context_keeps_state_and_reuses_adapted_class(self):
        native = AdminTextInputWidget(attrs={'data-custom': 'kept'})
        native.is_required = True
        widget = TranslatableFieldWidget([native])
        self.context(widget)
        adapted = type(native)
        self.context(widget)
        self.assertIs(type(native), adapted)
        self.assertEqual(native.attrs, {'class': 'vTextField', 'data-custom': 'kept'})
        self.assertTrue(native.is_required)
        other = TranslatableFieldWidget([AdminTextInputWidget()])
        self.context(other)
        self.assertIs(type(other.widgets[0]), adapted)

    def test_own_pair_formatter_keeps_priority_in_context_and_html(self):
        class PairAwareInput(forms.TextInput):
            def format_value(self, value):
                if isinstance(value, (list, tuple)):
                    lang, text = value
                    return [lang, str(text).upper()]
                return super().format_value(value)

        widget = TranslatableFieldWidget([PairAwareInput()])
        context = self.context(widget)
        self.assertEqual(next(context['widget']['subwidgets'])['value'], 'HALLO')
        html = widget.render('title', [('de', 'Hallo')], attrs={'id': 'id_title'})
        self.assertIn('value="HALLO"', html)

    def test_super_calls_formatter_before_original_parent(self):
        calls = []

        class ParentInput(forms.TextInput):
            def format_value(self, value):
                calls.append('parent')
                return super().format_value(value)

        class OwnInput(ParentInput):
            def format_value(self, value):
                calls.append('own')
                return super().format_value(value)

        native = OwnInput()
        self.context(TranslatableFieldWidget([native]))
        calls.clear()
        original_formatter = ValueFormatterMixin.format_value

        def tracked_formatter(instance, value):
            calls.append('formatter')
            return original_formatter(instance, value)

        with patch.object(ValueFormatterMixin, 'format_value', tracked_formatter):
            self.assertEqual(native.format_value('Hello'), 'Hello')
        self.assertEqual(calls, ['own', 'formatter', 'parent'])

    def test_forms_and_deepcopy_keep_independent_widgets(self):
        class TranslatedForm(forms.Form):
            title = TranslatableFieldFormField((forms.CharField(widget=AdminTextInputWidget()),),
                                               initial=TranslatableText().update(_origin='Origin', de='Hallo'))

        first = TranslatedForm().fields['title'].widget
        second = TranslatedForm().fields['title'].widget
        self.context(first)
        self.assertIs(type(second.widgets[0]), AdminTextInputWidget)
        self.assertNotIsInstance(second.widgets[0], ValueFormatterMixin)
        copied = copy.deepcopy(first)
        self.assertIs(type(copied.widgets[0]), type(first.widgets[0]))
        self.assertIsNot(copied.widgets[0], first.widgets[0])
        copied.widgets[0].attrs['data-custom'] = 'copy only'
        self.assertNotIn('data-custom', first.widgets[0].attrs)
        self.assertEqual(first.render('title', [('de', 'Hallo')], attrs={'id': 'id_title'}),
                         second.render('title', [('de', 'Hallo')], attrs={'id': 'id_title'}))

    def check_media_and_html(self, classes):
        value = TranslatableText().update(_origin='Origin', de='Hallo & Welt', en='Hello')
        for cls in classes:
            with self.subTest(widget=cls.__name__):
                native = cls()
                css, js = copy.deepcopy(native.media._css), list(native.media._js)
                widget = TranslatableFieldWidget([native])
                html = widget.render('title', value, attrs={'id': 'id_title'})
                self.assertEqual(native.media._css, css)
                self.assertEqual(native.media._js, js)
                self.assertIn('name="title_de"', html)
                self.assertIn('Hallo &amp; Welt', html)
                self.assertIn('name="title_en"', html)
                self.assertIn('Hello', html)
                self.assertEqual(copy.deepcopy(widget).render('title', value, attrs={'id': 'id_title'}), html)

    def test_media_and_html_of_native_widgets_are_preserved(self):
        self.check_media_and_html((forms.TextInput, AdminTextInputWidget, forms.Textarea, AdminTextareaWidget))

    @skipUnless(CKEditorWidget, 'Install django-ckeditor to exercise optional editor integration')
    def test_media_and_html_of_optional_editor_widgets_are_preserved(self):
        with patch('ckeditor_uploader.widgets.reverse', side_effect=lambda name: f'/{name}/'):
            self.check_media_and_html((CKEditorWidget, CKEditorUploadingWidget))

    def test_dynamic_media_overrides_do_not_restore_inherited_assets(self):
        calls = []

        class MediaParent(forms.TextInput):
            class Media:
                js = ('parent.js',)

        class DynamicMediaInput(MediaParent):
            @property
            def media(self):
                calls.append(self.media_js)
                return forms.Media(js=(self.media_js,))

        class InheritedMediaInput(DynamicMediaInput):
            class Media:
                js = ('own.js',)

        for cls, own_media in ((DynamicMediaInput, []), (InheritedMediaInput, ['own.js'])):
            with self.subTest(widget=cls.__name__):
                native = cls()
                native.media_js = 'first.js'
                self.assertEqual(native.media._js, ['first.js', *own_media])
                widget = TranslatableFieldWidget([native])
                self.context(widget)
                calls.clear()
                self.assertEqual(native.media._js, ['first.js', *own_media])
                self.assertEqual(calls, ['first.js'])
                native.media_js = 'second.js'
                calls.clear()
                self.assertEqual(native.media._js, ['second.js', *own_media])
                self.assertEqual(calls, ['second.js'])
                calls.clear()
                self.assertEqual(widget.media._js, ['second.js', *own_media, 'tof/js/translatable_fields_widget.js'])
                self.assertEqual(calls, ['second.js'])
