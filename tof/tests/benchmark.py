# -*- coding: utf-8 -*-
import timeit

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.utils import translation
from ..models import TranslatableField, StaticMessageTranslation
from django.utils.crypto import get_random_string

class Command(BaseCommand):
    def handle(self, *args, **options):
        n = 1000
        nruns = 10

        ct = ContentType.objects.get_for_model(StaticMessageTranslation)
        TranslatableField.objects.get_or_create(name='message', title='message', content_type=ct)

        new_messages = []

        for __ in range(n):
            instance = StaticMessageTranslation()
            translation.activate('en')
            en_title = instance.message = get_random_string(100)
            translation.activate('it')
            instance.title = f'it {en_title}'
            instance.save()
            new_messages.append(instance)

        ids = [m.pk for m in new_messages]

        print('TOF', timeit.timeit("""for m in StaticMessageTranslation.objects.filter(pk__in=ids): if not m.message.it.startswith('it'): raise ValueError(m.message)""", globals=globals(), number=1))
        print('TOF', timeit.timeit("""for m in StaticMessageTranslation.objects.filter(pk__in=ids): if not m.message.it.startswith('it'): raise ValueError(m.message)""", globals=globals(), number=nruns) / nruns)

        StaticMessageTranslation.objects.filter(pk__in=ids).delete()
