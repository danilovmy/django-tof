
from pathlib import Path
import importlib
from os import getenv, environ
import sys
from django.conf import ENVIRONMENT_VARIABLE
import django
if not getenv(ENVIRONMENT_VARIABLE):
    path = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(path.absolute()))
    environ[ENVIRONMENT_VARIABLE] = "tof.tests.settings"
    django.setup()

SOURCE = Path('tof')

def check_files():
    for file in SOURCE.rglob('*.py'):
        try:
            importlib.import_module('.'.join((*file.parts[0:-1], file.stem)))
        except ImportError as error:
            print(error, file)

if __name__ == '__main__':
    check_files()