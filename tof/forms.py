from functools import wraps

from django.contrib.contenttypes.models import ContentType
from django.forms import ModelForm


class TranslationsForm(ModelForm):

    class Media:
        js = ('tof/js/translation_form.js', )


class TranslationsInLineForm(ModelForm):

    def __init__(self, *args, parent_object=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_object = parent_object
        field = self.fields.get('field')
        if field:
            field.widget.widget.get_url = self.filter_ct(field.widget.widget.get_url)
            field.widget.can_add_related = field.widget.can_change_related = False

    def filter_ct(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            response = func(*args, **kwargs)
            if self.parent_object:
                return f'{response}?ct={ContentType.objects.get_for_model(self.parent_object).pk}'
            return response
        return wrapper
