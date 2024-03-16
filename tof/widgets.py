from django.contrib.admin.sites import all_sites
from django.forms.widgets import Media, MultiWidget
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.utils.safestring import mark_safe

from . import get_language


def resolve_admin_link(app_label, model, action):
    for site in all_sites:
        try:
            return reverse('admin:{}_{}_{}'.format(app_label, model, action), current_app=site.name)
        except NoReverseMatch:
            pass


class ValueFormatterMixin:

    def format_value(self, value):
        if isinstance(value, (list, tuple)):
            return [self.format_value(bit) for bit in value]
        return super().format_value(value)


class TranslatableFieldWidget(ValueFormatterMixin, MultiWidget):
    template_name = 'tof/multiwidget.html'
    input_type = 'text'
    _datadict = None

    def __init__(self, widgets, attrs=None):
        super().__init__(widgets, attrs=attrs)
        for widget in self.widgets:
            if not isinstance(widget, ValueFormatterMixin):
                widget.__class__.__bases__ = (ValueFormatterMixin,) + widget.__class__.__bases__

    def get_context(self, name, value, attrs):
        value = self.format_value(self.decompress(value))
        if value:
            self.widgets = self.widgets * len(value)
            self.widgets_names = [f'_{lang}' for lang, val in value]

        context = super().get_context(name, value, attrs)
        context['widget']['subwidgets'] = (self.rednder_subwidget(subwidget, **subwidget_context) for subwidget, subwidget_context in zip(self.widgets, context['widget']['subwidgets']))
        context['add_related_url'] = resolve_admin_link('tof', 'language', 'changelist')
        return context

    def id_for_label(self, id_):
        return super().id_for_label(id_).rpartition('_')[0]

    def decompress(self, value):
        return (type(value).__name__ == 'TranslatableText' and [*value.iter]) or (isinstance(value, (list, tuple)) and value) or [(get_language(), value or '')]

    @property
    def media(self):
        return super().media + Media(css={'all': ('tof/css/style.css', )},
                                     js=('tof/js/translatable_fields_widget.js', ))

    def value_from_datadict(self, data, __, name):
        if self._datadict is None:
            self._datadict = [(key.rpartition('_')[-1], val) for key, val in data.items() if key.startswith(f'{name}_')]
        return self._datadict

    def value_omitted_from_data(self, data, files, name):
        return not self.value_from_datadict(data, files, name)

    @staticmethod
    def rednder_subwidget(subwidget, **kwargs):
        kwargs['lang'], kwargs['value'] = kwargs['value']
        kwargs['attrs']['id'] = '{}_{}'.format(kwargs['attrs']['id'].rpartition('_')[0], kwargs['lang'])
        kwargs['render'] = lambda: mark_safe(subwidget.render(kwargs['name'], kwargs['value'], attrs=kwargs['attrs'], renderer=kwargs.get('renderer')))
        return kwargs


class TranslatableFieldHiddenWidget(TranslatableFieldWidget):

    def __init__(self, attrs=None):
        super().__init__(attrs)
        for widget in self.widgets:
            widget.input_type = 'hidden'
