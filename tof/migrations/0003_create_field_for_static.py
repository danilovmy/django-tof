# Generated by Django 3.2.9 on 2021-11-06 12:51
from django.db import migrations


def register_translated_field_in_static_translations(apps, schema_editor):
    model = apps.get_model('tof', 'staticmessagetranslation')
    ContentType = apps.get_model('contenttypes', 'ContentType').objects.get_for_model(model)
    TranslatableFieldManager = apps.get_model('tof', 'TranslatableField').objects
    __, created = TranslatableFieldManager.get_or_create(content_type=ContentType, name='translation')
    if created:
        print('successful added translated field for StaticMessageTranslation model')
    else:
        print('translated field for StaticMessageTranslation already exists')


def unregister_translated_field_in_static_translations(apps, schema_editor):
    model = apps.get_model('tof', 'staticmessagetranslation')
    ContentType = apps.get_model('contenttypes', 'ContentType').objects.get_for_model(model)
    TranslatableFieldManager = apps.get_model('tof', 'TranslatableField').objects
    deleted = TranslatableFieldManager.filter(content_type=ContentType, name='translation').delete()
    if deleted:
        print('successful removed translated field from StaticMessageTranslation model')
    else:
        print('translated field for StaticMessageTranslation model not found')


class Migration(migrations.Migration):

    dependencies = [
        ('tof', '0002_load_languages'),
    ]

    operations = [
        migrations.RunPython(register_translated_field_in_static_translations, reverse_code=unregister_translated_field_in_static_translations),
    ]
