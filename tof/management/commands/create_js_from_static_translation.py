import json
import os

from django.core.management import BaseCommand

from ...models import StaticMessageTranslation, Language


class Command(BaseCommand):
    help = '''
    Create js from static translation
    '''
    locale_dir = './media/langs/'

    def handle(self, *args, **options):
        translations = {lang: {} for lang in (self.get_lang_from_file(file) for file in self.get_files())}
        for message in self.get_translations_from_files():
            static, is_created = StaticMessageTranslation.objects.get_or_create(message=message)
            for lang, values in translations.items():
                values.update({message: getattr(static.translation, lang, f'{static.message}')})
        for file in self.get_files():
            with open(f'{self.locale_dir}{file}', 'w', encoding='utf-8') as f:
                f.write(json.dumps(translations[self.get_lang_from_file(file)], indent=2))

    def get_translations_from_files(self):
        translations = {}
        for file in self.get_files():
            lang = self.get_lang_from_file(file)
            with open(f'{self.locale_dir}{file}', 'r', encoding='utf-8') as f:
                json_str = f.read()
                if json_str:
                    for key, value in json.loads(json_str).items():
                        translation = translations[key] = translations.get(key) or {}
                        translation.update({lang: value})
        return translations

    def get_files(self):
        langs = Language.objects.values_list('iso', flat=True)
        return (file.name for file in os.scandir(self.locale_dir) if file.is_file() and file.name.endswith('.json') and self.get_lang_from_file(file.name) in langs)

    @staticmethod
    def get_lang_from_file(file_name):
        return file_name.removesuffix('.json')