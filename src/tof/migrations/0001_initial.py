# Generated by Django 5.0.3 on 2024-10-19 11:33

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Language',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('iso', models.CharField(max_length=2, unique=True)),
                ('is_active', models.BooleanField(default=True, verbose_name='Active')),
            ],
            options={
                'verbose_name': 'Language',
                'verbose_name_plural': 'Languages',
                'ordering': ['iso'],
            },
        ),
        migrations.CreateModel(
            name='StaticMessageTranslation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.CharField(max_length=1000, verbose_name='Message')),
                ('translation', models.CharField(max_length=1000, verbose_name='Translation')),
            ],
            options={
                'verbose_name': 'Static translation',
                'verbose_name_plural': 'Static translations',
                'indexes': [models.Index(fields=['message'], name='tof_staticm_message_cda2ef_idx')],
            },
        ),
        migrations.CreateModel(
            name='TranslatableField',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Name field', max_length=250, verbose_name='Field name')),
                ('content_type', models.ForeignKey(limit_choices_to=models.Q(('app_label', 'tof'), _negated=True), on_delete=django.db.models.deletion.CASCADE, related_name='translatablefields', to='contenttypes.contenttype')),
            ],
            options={
                'verbose_name': 'Translatable field',
                'verbose_name_plural': 'Translatable fields',
                'ordering': ('content_type', 'name'),
                'unique_together': {('content_type', 'name')},
            },
        ),
        migrations.CreateModel(
            name='Translation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField(help_text='First set the field')),
                ('value', models.TextField(help_text='Value field', verbose_name='Value')),
                ('content_type', models.ForeignKey(limit_choices_to=models.Q(('app_label', 'tof'), _negated=True), on_delete=django.db.models.deletion.DO_NOTHING, related_name='translations', to='contenttypes.contenttype')),
                ('field', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='translations', to='tof.translatablefield')),
                ('lang', models.ForeignKey(limit_choices_to=models.Q(('is_active', True)), on_delete=django.db.models.deletion.DO_NOTHING, related_name='translations', to='tof.language', to_field='iso')),
            ],
            options={
                'verbose_name': 'Translation',
                'verbose_name_plural': 'Translation',
                'unique_together': {('object_id', 'field', 'lang')},
            },
        ),
    ]
