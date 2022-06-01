import subprocess

from core.actions import ActionView
from settings import default_translator as _
from tof.management.commands.create_js_from_static_translation import Command


class GenerateTranslationJSONFileAction(ActionView):
    description = _('Generate translation JSON file for front')
    short_description = _('Generate translation JSON file for front')
    allow_empty = True
    finished_message = _('Success')

    def processing(self, *args, **kwargs):
        Command().handle()
        return super(GenerateTranslationJSONFileAction, self).processing(*args, **kwargs)


class VueI18NExtractAction(ActionView):
    description = _('Extract translation from front')
    short_description = _('Extract translation from front')
    allow_empty = True
    finished_message = _('Success')

    def processing(self, *args, **kwargs):
        result = subprocess.run('npm run vue-i18n-extract', shell=True, cwd='front_vue', capture_output=True)
        if result.returncode:
            return self.error(_('Error: {}').format(result.stderr.decode()))
        return super(VueI18NExtractAction, self).processing(*args, **kwargs)
