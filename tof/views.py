from django import forms
from django.contrib import messages
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.admin.options import get_content_type_for_model
from django.core.exceptions import ImproperlyConfigured
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string, select_template
from django.utils.decorators import classonlymethod
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.views.generic import FormView

from . import _


class YesNoMixIn:
    POSITIVE = 'yes'
    NEGATIVE = 'no'
    POSITIVE_TEXT = _('Yes, I\'m sure')
    NEGATIVE_TEXT = _('No, I\'m not sure')
    CHOICES = ((POSITIVE, POSITIVE_TEXT), (NEGATIVE, NEGATIVE_TEXT))
    button_template = '<button type=\"{submit}\" name=\"answer\" value=\"{value}\">{title}</button>'
    button_negative_template = '<a href="#" class="button cancel-link">{title}</a>'
    answer_help_text = answer_label = ''
    method = 'POST'
    process_url = ''
    form_template = 'core/extraform.html'

    def get_cleaned_data(self, *args, **kwargs):
        return self.cleaned_data if self.is_valid() else {}

    def get_cleaned_field(self, field=None, **kwargs):
        return self.get_cleaned_data().get(self.get_field_name(field))

    def get_field_name(self, field=None, **kwargs):
        return field or getattr(self, 'field', None) or list(self.fields.keys())[0]

    def get_request(self):
        return vars(self).get('request')

    def setup(self, *args, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)
        self.args = args
        answer = self.fields['answer']
        answer.choices = [self._get_choice('POSITIVE'), self._get_choice('NEGATIVE')]
        answer.label = self.answer_label
        answer.help_text = self.answer_help_text
        return self

    @cached_property
    def is_positiv(self):
        return self.get_cleaned_field() == self.POSITIVE

    def _get_choice(self, choice):
        return getattr(self, choice), getattr(self, '{}_TEXT'.format(choice))

    def _render_button(self, value, text, template=None):
        template = template or self.button_template
        return mark_safe(template.format(submit='submit', name=self.add_prefix('answer'), value=value, title=str(text)))

    def render_button_positive(self):
        return self._render_button(*self._get_choice('POSITIVE'))

    def render_button_negative(self):
        return self._render_button(*self._get_choice('NEGATIVE'), template=self.button_negative_template)


class YesNoForm(YesNoMixIn, forms.Form):
    prefix = 'YesNoForm'
    button_template = '<button type="{submit}" name="{name}" onclick="document.getElementById(`layer`).style.display = `block`;" value="{value}">{title}</button>'
    answer = forms.ChoiceField(choices=YesNoMixIn.CHOICES, widget=forms.RadioSelect())


class ActionView(FormView):
    ADDITION = ADDITION
    CHANGE = CHANGE
    DELETION = DELETION
    logger = LogEntry
    template_name = 'core/confirmation.html'
    template_name_suffix = 'confirmation'
    callback_template = None
    callback_template_name_suffix = 'callback'
    allow_empty = False
    short_description = ''
    description = ''
    counter = 0
    cancel_message = _('Action was cancelled')
    finished_message = ''
    processing_message = _('{} was change')
    extra_context = {'action_checkbox_name': ACTION_CHECKBOX_NAME}
    model = None
    admin = None
    queryset = None
    request = None
    permissions = ()
    permissions_message_error = _('You don\'t have enough permissions')
    template_button = 'core/action_button.html'
    error_message = 'Error {cause}'
    as_button = False

    @cached_property
    def answer(self):
        return YesNoForm(**super(ActionView, self).get_form_kwargs())

    @classmethod
    def name(cls):
        return cls.__name__

    def post(self, request, *args, **kwargs):
        if self.answer.is_valid():
            if self.answer.is_positiv:
                if self.get_form_class():  # answer is Positiv, processing with or without form
                    return super(ActionView, self).post(request, *args, **kwargs)  # form processing
                return self.processing(*args, **kwargs)  # processing without form
            return self.finished(cancel=True)  # answer is Negativ
        return self.get(request, *args, **kwargs)  # answer is not valid

    def get(self, request, *args, **kwargs):
        if self.get_form_class():
            self.request.method = 'GET'
            return super(ActionView, self).get(request, *args, **kwargs)
        return self.render_to_response(self.get_context_data(**kwargs))

    def form_valid(self, *args, **kwargs):
        """Make something ready befor processing."""
        return self.processing(*args, **kwargs)

    def processing(self, *args, **kwargs):
        return self.finished(*args, **kwargs)

    def finished(self, *__, **kwargs):
        """Send message after process and return None."""
        message = kwargs.get('message') or self.finished_message
        if message:
            self.info(message, **kwargs)

    def cancel(self, *__, **kwargs):
        """Send cancel message during process and return None."""
        if kwargs.get('error'):
            self.error(getattr(kwargs['error'], 'message', None) or getattr(kwargs['error'], '__cause__', None) or kwargs['error'], **kwargs)
        self.warning(kwargs.get('message') or self.cancel_message, **kwargs)

    def get_form(self, form_class=None, **kwargs):
        form = super(ActionView, self).get_form(form_class)
        form.request = self.request
        if hasattr(form, 'setup'):
            return form.setup(request=self.request, **dict({'prefix': self.get_prefix()}, **kwargs))
        return form

    def get_prefix(self):
        return getattr(self, 'prefix', None)

    @classonlymethod
    def as_view(cls, **initkwargs):
        response = super(ActionView, cls).as_view(**initkwargs)
        response.short_description = cls.short_description
        response.__name__ = cls.__name__
        return response

    def dispatch(self, admin, request, queryset, *args, **kwargs):
        if self.check_permissions(request, admin):
            return super(ActionView, self).dispatch(request, *args, **kwargs)
        return self.cancel(self.permissions_message_error)

    def setup(self, admin, request, queryset, *args, **kwargs):
        vars(self).update(admin=admin, model=admin.model, queryset=queryset)
        return super(ActionView, self).setup(request, *args, **kwargs)

    @classmethod
    def check_permissions(cls, request, admin=None):
        return request.user.is_superuser or not getattr(cls, 'permissions', None) or (
            request.user.has_perms(permission.format(model_name=admin.opts.model_name, app_label=admin.opts.app_label) for permission in cls.permissions))

    @classmethod
    def patch_request_data(cls, data):
        if cls.allow_empty and not data.getlist(ACTION_CHECKBOX_NAME):
            data._mutable = True  # pylint: disable=W0212
            data[ACTION_CHECKBOX_NAME] = '-1'
            data._mutable = False  # pylint: disable=W0212
        return data

    @classmethod
    def get_as_tuple(cls):
        return cls.as_view(), cls.name(), cls.short_description

    def get_queryset(self, *args, **kwargs):
        if self.queryset is None:
            if self.model:
                self.queryset = self.model.objects.none()
            elif self.admin:
                self.queryset = self.admin.queryset(self.request).none()
        return self.queryset

    def get_object(self):
        for obj in self.get_queryset():
            return obj

    def log(self, obj, action_flag=CHANGE, **kwargs):
        LogEntry.objects.log_action(
            user_id=self.request.user.pk,
            content_type_id=get_content_type_for_model(obj).pk,
            object_id=obj.pk,
            object_repr=str(obj),
            action_flag=action_flag,
            change_message=kwargs.get('change_message') or self.processing_message.format(obj, **kwargs),
        )

    def info(self, info, **kwargs):
        info = str(info.format(counter=self.counter, **kwargs))
        getattr(messages, kwargs.get('message_type') or 'info', messages.info)(self.request, info)
        return info

    def error(self, cause, **kwargs):
        return self.info(self.error_message, message_type='error', cause=cause, **kwargs)

    def warning(self, warning, **kwargs):
        return self.info(warning, message_type='warning', **kwargs)

    def get_template_names(self):
        try:
            return super(ActionView, self).get_template_names()
        except ImproperlyConfigured:
            opts = self.model._meta
            return ['admin/{}/{}/{}_{}.html'.format(opts.app_label, opts.object_name, self.name(), self.callback_template_name_suffix).lower(),
                    'admin/{}/{}_{}.html'.format(opts.app_label, self.name(), self.template_name_suffix).lower(),
                    'admin/{}_{}.html'.format(self.name(), self.template_name_suffix).lower(),
                    'admin/{}.html'.format(self.template_name_suffix).lower()]

    def get_callback_template(self):
        self.template_name = self.callback_template
        self.template_name_suffix = self.callback_template_name_suffix

        templates = self.get_template_names()

        delattr(self, 'template_name')
        delattr(self, 'template_name_suffix')

        try:
            return select_template(templates).name
        except TemplateDoesNotExist:
            return ''

    def get_context_data(self, **kwargs):
        opts = self.model._meta  # pylint: disable=protected-access
        context = {
            'title': '%s. %s' % (str(self.short_description), str(_(u'Are you sure?'))),
            'action_short_description': self.short_description,
            'action_description': self.description,
            'action_name': self.name(),
            'objects_name': force_str(opts.verbose_name_plural),
            'action_objects': [self.get_queryset()],
            'callback_template': self.get_callback_template(),
            'queryset': self.get_queryset(),
            'opts': opts,
            'app_label': opts.app_label,
            'answer_form': self.answer,
        }

        if not self.get_form_class():
            context['form'] = ''
        context.update(kwargs)
        context.update(self.extra_context)
        return super().get_context_data(**context)

    @classmethod
    def render_as_button(cls):
        return render_to_string(cls.template_button, {'action_name': cls.name(), 'action_short_description': cls.short_description})


class ActionViewsMixin:

    def changelist_view(self, request, extra_context=None):
        data = request.POST
        action = data.getlist('action') and data.getlist('action')[int(data.get('index', 0))]
        if data and not data.get('_save') and action and not data.getlist(ACTION_CHECKBOX_NAME):
            action = self.get_actions(request).get(action)
            if getattr(action and action[0], 'view_class', None):
                request.POST = action[0].view_class.patch_request_data(data)
        extra_context = extra_context or {}
        extra_context = {'buttons': [action[0].view_class.render_as_button for action in self.get_actions(request).values() if
                                     hasattr(action[0], 'view_class') and action[0].view_class.as_button] + extra_context.get('buttons', [])} | extra_context
        return super().changelist_view(request, extra_context)

    def get_actions(self, request):
        return {key: action for key, action in super().get_actions(request).items() if not hasattr(action[0], 'view_class') or action[0].view_class.check_permissions(request, self)}

    def get_changelist_instance(self, request):
        changelist = super().get_changelist_instance(request)
        changelist.show_admin_actions = changelist.show_admin_actions or any(getattr(getattr(action[0], 'view_class', None), 'allow_empty', None) for action in self.get_actions(request).values())
        return changelist