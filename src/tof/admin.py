import logging

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.options import IS_POPUP_VAR
from django.contrib.admin.widgets import AutocompleteSelect
from django.contrib.contenttypes.admin import GenericInlineModelAdmin, GenericStackedInline, GenericTabularInline
from django.contrib.contenttypes.forms import BaseGenericInlineFormSet
from django.contrib.contenttypes.models import ContentType
from django.db.models import DO_NOTHING, CharField, ForeignKey, Q, TextField
from django.forms.models import ModelChoiceIterator

from .actions import GenerateTranslationJSONFileAction, VueI18NExtractAction
from .forms import TranslationsForm, TranslationsInLineForm
from .models import Language, StaticMessageTranslation, TranslatableField, Translation
from .views import ActionViewsMixin

# Get an instance of a logger
logger = logging.getLogger('django')
translation_adminsite_name = getattr(settings, 'TRANSLATION_ADMINSITE', 'translation-admin')
TranslationSiteAdmin = next((site for site in admin.sites.all_sites if site.name == translation_adminsite_name), None) or admin.sites.site

@admin.register(ContentType, site=TranslationSiteAdmin)
class ContentTypeAdmin(admin.ModelAdmin):
    search_fields = ('app_label', 'model')

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        return queryset.filter(~Q(app_label='tof')).order_by('app_label', 'model'), use_distinct

    def has_add_permission(self, *args, **kwargs):
        return False

    def has_change_permission(self, *args, **kwargs):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False


@admin.register(Language, site=TranslationSiteAdmin)
class LanguageAdmin(admin.ModelAdmin):
    search_fields = ('iso', )
    list_display = ('iso', 'is_active')
    list_editable = ('is_active', )

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        query = Q(is_active=True) if IS_POPUP_VAR in request.GET or 'autocomplete' in request.path else Q()
        return queryset.filter(query), use_distinct

    def has_view_permission(self, request, obj=None):
        return True


class ModelFieldIterator:

    def __init__(self, field):
        self.field = field

    @property
    def id(self):
        return f'{self.field.name}'

    @property
    def name(self):
        return f'{self.field.name}'

    def __str__(self):
        return f'{self.id}'


@admin.register(TranslatableField, site=TranslationSiteAdmin)
class TranslatableFieldAdmin(admin.ModelAdmin):
    search_fields = ('content_type__model', 'name')
    list_display = ('content_type', 'name')

    fieldsets = (None, {'fields': ['content_type', 'name']}),

    autocomplete_fields = ('content_type',)

    class Media:
        js = ('tof/js/autocomplete_utils.js',)
        css = {'screen': ('admin/css/empty_containers.css',)}

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request) or {}
        return initial | {'name': []}

    def get_queryset(self, request):
        return super().get_queryset(request).exclude(content_type=ContentType.objects.get_for_model(StaticMessageTranslation))

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.delete()

    def has_change_permission(self, *args, **kwargs):
        return False

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'name':
            field = ForeignKey(TranslatableField, name='field', on_delete=DO_NOTHING, to_field='name')
            vars(field).update(model=Translation, queryset=field.related_model.objects.none(), empty_label=None)
            kwargs['widget'] = AutocompleteSelect(field, self.admin_site, choices=ModelChoiceIterator(field))
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == 'content_type':
            field.widget.attrs.update({'onchange': 'concrete_search(this);', 'data-name': 'name'})
            field.queryset = field.queryset

        return field

    def get_search_results(self, request, queryset, search_term):
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return self.get_search_results_for_ajax(request, queryset, search_term)
        return super().get_search_results(request, queryset, search_term)

    def get_search_results_for_ajax(self, request, queryset, *__, **___):
        try:
            content_type = ContentType.objects.get_for_id(request.GET.get('content_type') or 0)
        except ContentType.DoesNotExist:
            return (), False
        existed = queryset.filter(content_type=content_type).values_list('name', flat=True)
        return [ModelFieldIterator(field) for field in content_type.model_class()._meta.get_fields() if isinstance(field, (TextField, CharField)) and field.column != 'password' and field.name not in existed], False


@admin.register(Translation, site=TranslationSiteAdmin)
class TranslationAdmin(admin.ModelAdmin):
    form = TranslationsForm
    list_display = ('content_object', 'lang', 'field', 'value')
    list_filter = 'content_type',
    fieldsets = (None, {'fields': (('field','lang'), 'object_id', 'value')}), ('hidden', {'classes': ['hidden'], 'fields': ['content_type']})
    autocomplete_fields = ('field', 'lang')
    url_name = '%s:%s_%s_autocomplete'

    def get_readonly_fields(self, request, obj):
        response = list(super().get_readonly_fields(request, obj))
        if obj and obj.pk:
            response.extend(['field', 'object_id'])
        return tuple(response)


class TranslationFormSet(BaseGenericInlineFormSet):
    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['parent_object'] = self.instance
        return kwargs


class TranslationInlineMixin:
    model = Translation
    extra = 0
    autocomplete_fields = ('field', 'lang')
    fields = ('field', 'lang', 'value')
    formset = TranslationFormSet
    form = TranslationsInLineForm

    @property
    def media(self):
        return super().media + forms.Media(js=('tof/js/translation_inline.js', ))


class TranslationInline(TranslationInlineMixin, GenericInlineModelAdmin):
    pass


class TranslationStackedInline(TranslationInline, GenericStackedInline):
    pass


class TranslationTabularInline(TranslationInline, GenericTabularInline):
    pass


@admin.register(StaticMessageTranslation, site=TranslationSiteAdmin)
class StaticMessageTranslationAdmin(ActionViewsMixin, admin.ModelAdmin):
    fields = ('message', 'translation')
    search_fields = ('message', 'translation')
    readonly_fields = ('message', 'languages')
    list_display = ('__str__', 'languages')
    actions = (GenerateTranslationJSONFileAction.as_view(), VueI18NExtractAction.as_view())

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm('accounts.is_translator')

    def get_queryset(self, request):
        return super().get_queryset(request).distinct()
