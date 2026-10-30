![GitHub issues](https://img.shields.io/github/issues/danilovmy/django-tof.svg)
![GitHub stars](https://img.shields.io/github/stars/danilovmy/django-tof.svg)
![GitHub Release Date](https://img.shields.io/github/release-date/danilovmy/django-tof.svg)
![GitHub commits since latest release](https://img.shields.io/github/commits-since/danilovmy/django-tof/latest.svg)
![GitHub last commit](https://img.shields.io/github/last-commit/danilovmy/django-tof.svg)
[![GitHub license](https://img.shields.io/github/license/danilovmy/django-tof)](https://github.com/danilovmy/django-tof/blob/master/LICENSE)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/ef1b0b5bb51048a6a03f3cc87798f9f9)](https://www.codacy.com/manual/danilovmy/django-tof?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=danilovmy/django-tof&amp;utm_campaign=Badge_Grade)
[![codecov](https://codecov.io/gh/danilovmy/django-tof/branch/master/graph/badge.svg)](https://codecov.io/gh/danilovmy/django-tof)

[![PyPI](https://img.shields.io/pypi/v/django-tof.svg)](https://pypi.python.org/pypi/django-tof)
[![PyPI](https://img.shields.io/pypi/pyversions/django-tof.svg)]()
![PyPI - Downloads](https://img.shields.io/pypi/dm/django-tof.svg?label=pip%20installs&logo=python)

# django-tof
Django models translation on fly 🛸️
THIS FORK IS THE NEXT VERSION OF DJANGO_TOF V 1.0
----
This project was initiated, promoted and accompanied by winePad GmbH (winePad.at). All development based on ideas, experience and support from Maxim Danilov (winePad GmbH).
----

[![IMAGE ALT TEXT HERE](https://img.youtube.com/vi/i0QJJJEMKSU/0.jpg)](https://www.youtube.com/watch?v=i0QJJJEMKSU)

_[Russian readme](README_ru.md)_

----
The background and objectives of this projects are described [here](https://github.com/danilovmy/django-tof/wiki/django-tof)

An Application for dynamic translation of existing Django models into any number of languages.

  - without need to change existing model classes
  - without need to reboot servers
  - without changing the use of translated fields
  - ready to work after install and indicated in INSTALLED_APPS
  - fully integrated in Django modelAdmin, and ModelInline

## Installation

`pip install git+https://github.com/danilovmy/django-tof.git`
`python manage.py migrate tof`

~~~python
# settings.py
...
INSTALLED_APPS = [
...
'tof',
...
]
~~~

Don't forget to do if it necessary:
`python manage.py collectstatic`

## How to use

Add an existing text field to TOF's "Translatable fields" in the admin. TOF
attaches the descriptor and translation behavior at runtime; the business model
and its normal `ModelAdmin` do not require a TOF base class. Assigning a string
updates the current Django language. Admin forms offer the available languages.

For individual translation rows, add `TranslationTabularInline` or
`TranslationStackedInline` from `tof.admin` to your normal admin's `inlines`.

![Widget for translatable fields](https://raw.githubusercontent.com/danilovmy/django-tof/master/docs/images/field_with_langs.jpeg)

## Programmatic use
Like a standard using, but it is possible to get a specific translation.

~~~python
from django.utils.translation import activate

activate('en')
book = Book.objects.first()
book.title  # => Title en
book.title.de  # => Title de
~~~

## Settings and query behavior

`DEFAULT_LANGUAGE` in Django settings defaults to `"en"`. Field display uses the
current Django language, then the default language, another nonempty translation,
and finally the original database value. Language codes use their first two
characters. `LANGUAGES_SOURCE` defaults to `tof.models.Language` and supplies the
admin language choices; `TRANSLATION_ADMINSITE` can select a custom admin site.

On PostgreSQL, the native Django compiler loads translations in the same SELECT.
Filtering searches the original value and all translations. An implicit exact
lookup (`filter(title="hello")`) matches translations without regard to case;
explicit `title__exact="hello"` preserves case sensitivity. The original column
keeps Django's normal lookup behavior. Ordering uses the displayed translation,
including `Meta.ordering`, admin ordering, related fields, and expressions, before
pagination. Managers and business model definitions do not need to change.

Other database backends keep Django's native compiler. Translation access can
load extra queries there; translated filtering and ordering require PostgreSQL.
The obsolete `FALLBACK_LANGUAGES`, `DEFAULT_FILTER_LANGUAGE`, and
`CHANGE_DEFAULT_MANAGER` settings are no longer used.

## Compatibility and upgrade

- Python 3.10–3.12; Django 4.2.x or 5.0.x (`>=4.2,<5.1`).
- PostgreSQL 12 or newer for translated queries (verified locally on 14.21).
- `psycopg[binary]>=3.1.8,<4` is installed because the compiler imports Django's
  PostgreSQL expressions. CKEditor is optional and is not a runtime dependency.

The existing TOF migration history and `Language.id` are preserved. Translation
foreign keys continue to store ISO codes through `Language.iso`. Upgrading does
not require changing business models or regenerating TOF migrations. Filtering
now searches every translation, and default ordering now follows the displayed
translation; review callers relying on the previous behavior.

## Development and tests

Install the package and build tools with `python -m pip install -e ".[dev]"`.
The optional `[test]` extra enables the CKEditor widget regression.
Configure a dedicated PostgreSQL database with `TOF_DB_NAME`, `TOF_DB_USER`,
`TOF_DB_PASSWORD`, `TOF_DB_HOST`, `TOF_DB_PORT`, and `TOF_TEST_DB_NAME`.
Defaults are `tof_library`, `tof_test`, an empty password, `127.0.0.1`, `5432`,
and `test_tof_library`. The user must be allowed to create the test database.

```console
python -m django test tests --settings=tests.settings --keepdb --noinput
python -m build
```

`TOF_DB_ENGINE=django.db.backends.sqlite3` runs the DB-independent tests and
SQLite smoke checks, skipping PostgreSQL query regressions. The wheel contains
only `tof`, including its migrations, templates, static assets, and language
fixture. The source distribution additionally includes the standalone tests.
