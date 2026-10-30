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

----
Этот проект был инициирован, продвигался и сопровождался winePad GmbH (winePad.at). Разработка полностью основана на идеях, опыте и поддержике Максима Данилова из winePad GmbH.
----

[![IMAGE ALT TEXT HERE](https://img.youtube.com/vi/i0QJJJEMKSU/0.jpg)](https://www.youtube.com/watch?v=i0QJJJEMKSU)

----
Предпосылки и цели этого проекта описаны [тут](https://github.com/danilovmy/django-tof/wiki/django-tof)

Приложение для перевода динамического содержимого существующих моделей Django на произвольное количество языков

  - без необходимости изменения исходных классов моделей
  - без необходимости перезапуска сервера
  - без изменения схемы использования переводимых полей
  - готов к работе сразу после установки и указании в INSTALLED_APPS
  - полностью интегрирован в админку Django.

## Установка

`pip install git+https://github.com/danilovmy/django-tof.git` #egg=tof&subdirectory=src"

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
Не забудьте сделать при необходимости

`python manage.py collectstatic`
## Использование

Добавьте существующее текстовое поле в "Translatable fields" в админке TOF.
Descriptor и поведение переводов подключаются во время работы. Бизнес-модели и
обычному `ModelAdmin` специальный базовый класс TOF не нужен. Присваивание строки
обновляет перевод текущего языка Django. Формы админки показывают доступные языки.

Для отдельных строк переводов добавьте `TranslationTabularInline` или
`TranslationStackedInline` из `tof.admin` в `inlines` обычной админки.

![Widget for translatable fields](https://raw.githubusercontent.com/danilovmy/django-tof/master/docs/images/field_with_langs.jpeg)

## Использование программно

Ни чем не отличается от стандартного, но имеется возможность получить специфичный перевод.

~~~python
from django.utils.translation import activate

activate('en')
book = Book.objects.first()
book.title  # => Title en
book.title.de  # => Title de
~~~

## Настройки и запросы

`DEFAULT_LANGUAGE` в настройках Django по умолчанию равен `"en"`. Для отображения
используется текущий язык Django, затем язык по умолчанию, другой непустой перевод
и исходное значение столбца. Используются первые два символа кода языка.
`LANGUAGES_SOURCE` по умолчанию равен `tof.models.Language` и задаёт языки в
админке. `TRANSLATION_ADMINSITE` позволяет выбрать свою админку.

На PostgreSQL переводы загружаются тем же SELECT через нативный compiler Django.
Фильтрация проверяет исходное значение и переводы на всех языках.
`filter(title="hello")` ищет переводы без учёта регистра;
`filter(title__exact="hello")` сохраняет чувствительность к регистру.
Для физического столбца действуют обычные правила lookup Django.
Сортировка использует отображаемый перевод до пагинации, включая `Meta.ordering`,
админку, связанные поля и выражения. Менеджеры и бизнес-модели менять не нужно.

Другие СУБД используют нативный compiler Django; чтение переводов может требовать
дополнительных запросов. Поиск и сортировка по переводам требуют PostgreSQL.
Настройки `FALLBACK_LANGUAGES`, `DEFAULT_FILTER_LANGUAGE` и
`CHANGE_DEFAULT_MANAGER` больше не используются.

## Совместимость и обновление

- Python 3.10–3.12, Django 4.2.x или 5.0.x (`>=4.2,<5.1`).
- PostgreSQL от 12 для переводных запросов; локально проверена версия 14.21.
- `psycopg[binary]>=3.1.8,<4` устанавливается вместе с библиотекой: compiler
  импортирует PostgreSQL expressions Django. CKEditor остаётся необязательным.

История миграций TOF и `Language.id` сохранены. FK переводов по-прежнему хранит
ISO-код через `Language.iso`. Пересоздавать миграции и менять бизнес-модели при
обновлении не требуется. Фильтрация теперь учитывает все переводы, а базовая
сортировка — отображаемый перевод; проверьте места, зависящие от старого поведения.

## Разработка и проверки

Установка инструментов: `python -m pip install -e ".[dev]"`.
Дополнение `[test]` включает тест виджета CKEditor.
Для отдельной тестовой PostgreSQL задайте `TOF_DB_NAME`, `TOF_DB_USER`,
`TOF_DB_PASSWORD`, `TOF_DB_HOST`, `TOF_DB_PORT`, `TOF_TEST_DB_NAME`.
Значения по умолчанию: `tof_library`, `tof_test`, пустой пароль, `127.0.0.1`,
`5432`, `test_tof_library`. Пользователю нужно право создания тестовой БД.

```console
python -m django test tests --settings=tests.settings --keepdb --noinput
python -m build
```

При `TOF_DB_ENGINE=django.db.backends.sqlite3` выполняются независимые от БД
проверки и SQLite smoke; регрессии PostgreSQL пропускаются. Wheel содержит
только `tof` с миграциями, шаблонами, static и языковой fixture.
В source distribution также входят самостоятельные тесты.
