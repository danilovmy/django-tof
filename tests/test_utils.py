from django.contrib.admin.utils import display_for_field
from django.db import models
from django.test import SimpleTestCase, override_settings
from django.utils import translation
from django.utils.crypto import get_random_string
from tof.utils import TranslatableText


class TestTranslatableTextIntegration(SimpleTestCase):

    def setUp(self):
        self.addCleanup(translation.activate, translation.get_language())
        self.test_obj = TranslatableText()
        self.random_english = get_random_string(20)

    @override_settings(DEFAULT_LANGUAGE='en')
    def test_admin_displays_translated_field_and_fallbacks(self):
        field = models.CharField(max_length=255)
        field.set_attributes_from_name('title')
        value = TranslatableText().update(de='  Titel  ', en=' English ', _origin='Original')
        for language, expected in [('de', 'Titel'), ('fr', 'English')]:
            with self.subTest(language=language), translation.override(language):
                self.assertEqual(display_for_field(value, field, '-'), display_for_field(str(value), field, '-'))
                self.assertEqual(value.strip(), expected)
        with translation.override('de'):
            self.assertEqual(value.strip(' T'), 'itel')
        with translation.override('fr'):
            for attrs in ({'_origin': 'Original'}, {}, {'fr': '  '}):
                with self.subTest(attrs=attrs):
                    value = TranslatableText().update(**attrs)
                    self.assertEqual(display_for_field(value, field, '-'), display_for_field(str(value), field, '-'))
                    self.assertEqual(value.strip(), str(value).strip())

    def test_integration_language_normal(self):
        random_russian = get_random_string(20)
        self.test_obj.ru = random_russian
        translation.activate('ru')

        self.assertEqual(str(self.test_obj), random_russian, msg='str representation should be value of ru attr')

        random_str = get_random_string(20)
        self.assertEqual(self.test_obj + random_str, f'{random_russian}{random_str}', msg='should merge value of ru attr with random_str')

        self.assertEqual(random_str + self.test_obj, f'{random_str}{random_russian}', msg='should merge random_str with value of ru attr')

        self.assertEqual(len(self.test_obj), 20, msg='should return the length of the attribute of ru')

        self.assertTrue(bool(self.test_obj), msg='should return in obj has value')

        self.assertEqual(list(m for m in random_russian), list(m for m in self.test_obj))

        self.assertEqual(self.test_obj['ru'], random_russian, msg='should get value of the attr ru')

        self.assertTrue(self.test_obj == random_russian, msg='should call be equal to random russian')

        object_dict = "dict_keys(['ru'])"
        self.assertEqual(f'{self.test_obj!r}', f'{random_russian} {object_dict}', msg='should return str representation with keys')

        self.assertEqual(self.test_obj.get_lang(), 'ru', msg='should be the set language')

        del self.test_obj['ru']
        with self.assertRaises(AttributeError):
            self.test_obj.ru

    def test_integration_empty_language_no_origin(self):
        random_german = ''
        self.test_obj.de = random_german
        translation.activate('de')

        self.assertEqual(str(self.test_obj), '', msg='str representation should be value of de attr which is an empty str')

        random_str = get_random_string(20)
        self.assertEqual(self.test_obj + random_str, random_str, msg='should return random_str')

        self.assertEqual(random_str + self.test_obj, random_str, msg='should return random_str')

        self.assertEqual(len(self.test_obj), 0, msg='should return the length of the attribute of de which is 0')

        self.assertFalse(bool(self.test_obj), msg='should return in obj has value')

        self.assertEqual(list(m for m in self.test_obj), [], msg='test_obj should be empty')

        self.assertIsNone(self.test_obj['de'], msg='should be None')

        self.assertTrue(self.test_obj == '', msg='should call be equal to empty str')

        self.assertEqual(f'{self.test_obj!r}', ' dict_keys([])', msg='should return empty keys dict')

        self.assertEqual(self.test_obj.get_lang(), 'de', msg='should be the set language')

    def test_integration_empty_language_with_origin(self):
        random_russian = get_random_string(20)
        random_german = ''
        self.test_obj._origin = random_russian
        self.test_obj.de = random_german
        translation.activate('de')

        self.assertEqual(str(self.test_obj), random_russian, msg='str representation should be value of the _origin attr')

        random_str = get_random_string(20)
        self.assertEqual(self.test_obj + random_str, f'{random_russian}{random_str}', msg='should return random_russian merged with random_str')

        self.assertEqual(random_str + self.test_obj, f'{random_str}{random_russian}', msg='should return random_str merged with random_russian')

        self.assertEqual(len(self.test_obj), 20, msg='should return the length of the attribute _origin')

        self.assertTrue(bool(self.test_obj), msg='should return in obj has value')

        self.assertEqual(list(m for m in random_russian), list(m for m in self.test_obj))

        self.assertIsNone(self.test_obj['de'], msg='should be None')

        self.assertTrue(self.test_obj == random_russian, msg='should call be equal to random russian')

        object_dict = "dict_keys(['_origin'])"
        self.assertEqual(f'{self.test_obj!r}', f'{random_russian} {object_dict}', msg='should return str representation with keys')

        self.assertEqual(self.test_obj.get_lang(), 'de', msg='should be the set language')

    def test_integration_empty_language_fallback(self):
        random_german = ''
        random_english = get_random_string(20)
        self.test_obj.de = random_german
        self.test_obj.en = random_english
        translation.activate('de')

        with self.assertRaises(AttributeError, msg='attribute shold not be set'):
            self.test_obj.de

        self.assertEqual(str(self.test_obj), random_english, msg='str representation should be value of the _origin attr')

        random_str = get_random_string(20)
        self.assertEqual(self.test_obj + random_str, f'{random_english}{random_str}', msg='should return random_english merged with random_str')

        self.assertEqual(random_str + self.test_obj, f'{random_str}{random_english}', msg='should return random_str merged with random_english')

        self.assertEqual(len(self.test_obj), 20, msg='should return the length of the attribute _origin')

        self.assertTrue(bool(self.test_obj), msg='should return in obj has value')

        self.assertEqual(list(m for m in random_english), list(m for m in self.test_obj))

        self.assertIsNone(self.test_obj['de'], msg='should be None')

        self.assertTrue(self.test_obj == random_english, msg='should call be equal to random english')

        object_dict = "dict_keys(['en'])"
        self.assertEqual(f'{self.test_obj!r}', f'{random_english} {object_dict}', msg='should return str representation with keys')

        self.assertEqual(self.test_obj.get_lang(), 'de', msg='should be the set language')

    def test_get_language(self):

        self.assertIsNone(self.test_obj.current, msg='should be none as no language is set')

        random_german = get_random_string(20)
        self.test_obj.de = random_german
        translation.activate('de')
        self.assertEqual(self.test_obj.current, random_german, msg='should be value of attr de')

        random_str = get_random_string(5)
        translation.activate(random_str)
        self.assertEqual(self.test_obj.get_lang(), random_str[:2].lower(), msg='should only be the first two letters of set language')

        random_str = get_random_string(20)
        translation.activate('en')
        self.test_obj.update_current(random_str)
        self.assertEqual(self.test_obj.en, random_str, msg='should create attr of current lang and set value to it')


class TestTranslatableText(SimpleTestCase):

    def setUp(self):
        self.addCleanup(translation.activate, translation.get_language())
        self.test_obj = TranslatableText()

    def test___setattr__(self):
        random_str = get_random_string(30)
        self.test_obj.__setattr__('ru', random_str)
        self.assertEqual(self.test_obj.ru, random_str, msg='attr should be set to random str')

        self.test_obj.__setattr__('en', True)
        self.assertEqual(self.test_obj.en, 'True', msg='attr should be set to str representation of True')

        self.test_obj.__setattr__('more_than_two', None)
        self.assertEqual(self.test_obj.more_than_two, '', msg='attr should be set to empty str')

        random_str = get_random_string(30)
        self.test_obj.__setattr__('also_more_than_two', random_str)
        self.assertEqual(self.test_obj.also_more_than_two, random_str, msg='attr should be set to random str')

        self.test_obj.__setattr__('de', None)
        self.assertNotIn('de', vars(self.test_obj), msg='attr should not be set')

    def test___setitem__(self):
        class TestSubClass(type(self.test_obj)):

            def __setattr__(self, attr, value):
                vars(self)[attr] = value

        test_obj = TestSubClass()

        random_str = get_random_string(30)
        test_obj.__setitem__('some_attr', random_str)
        self.assertEqual(test_obj.some_attr, random_str, msg='attr should be set to random str')

        test_obj.__setitem__(3, 'not_important')
        self.assertNotIn(3, vars(test_obj), msg='attr should not be set')

        test_obj.__setitem__(True, 'not_important')
        self.assertNotIn(True, vars(test_obj), msg='attr should not be set')

        test_obj.__setitem__(None, 'not_important')
        self.assertNotIn(None, vars(test_obj), msg='attr should not be set')

        test_obj.__setitem__(str(True), 'not_important')
        self.assertIn('True', vars(test_obj), msg='attr True should be set')

    def test___delattr__(self):
        random_str = get_random_string(20)
        self.test_obj.__dict__[random_str] = 'not_important'
        self.assertIn(random_str, vars(self.test_obj), msg='attr should be set')
        self.assertEqual(getattr(self.test_obj, random_str), 'not_important', msg='attr should be the set string')

        self.test_obj.__delattr__(random_str)
        self.assertNotIn(random_str, vars(self.test_obj), msg='attr should be deleted')

    def test_update(self):

        class TestClass(type(self.test_obj)):

            def __setattr__(self, attr, value):
                vars(self)[attr] = value

        random_str_1 = get_random_string(20)
        random_str_2 = get_random_string(20)
        test_obj = TestClass()
        test_kwargs = {'first_key': random_str_1, 'second_key': random_str_2}
        test_obj.update(**test_kwargs)

        self.assertEqual(test_obj.first_key, random_str_1, msg='attr should be set to random_str_1')
        self.assertEqual(test_obj.second_key, random_str_2, msg='attr should be set to random_str_2')

        self.assertEqual(test_obj.update(kwarg='some_kwarg'), test_obj, msg='should return self')

    def test_iter(self):
        translation.activate('nl')
        random_german = get_random_string(20)
        random_english = get_random_string(20)

        self.test_obj.DEFAULT = 'en'
        self.test_obj.de = random_german
        self.test_obj.en = random_english
        self.test_obj.too_long = 'not_important'

        expected_output = [('en', random_english), ('de', random_german)]
        output = [m for m in self.test_obj.iter]
        self.assertEqual(output, expected_output, msg='should match the expected output')

        translation.activate('nl')
        random_russian = get_random_string(20)
        self.test_obj.DEFAULT = 'ru'
        self.test_obj.nl = None
        self.test_obj.ru = random_russian
        expected_output = [('ru', random_russian), ('de', random_german), ('en', random_english)]
        output = [m for m in self.test_obj.iter]
        self.assertEqual(output, expected_output, msg='should match the expected output')

    def test_mapping_and_string_protocols(self):
        with translation.override('de'):
            value = TranslatableText().update(_origin='Origin', de='Hallo', en='Hello')
            self.assertEqual(value[1:4], 'all')
            self.assertEqual(list(value), list('Hallo'))
            del value['de']
            self.assertIsNone(value['de'])
            self.assertEqual(str(value), 'Hello')
            del value['en']
            self.assertEqual(str(value), 'Origin')
            del value['_origin']
            self.assertFalse(value)
            self.assertEqual(len(value), 0)

    def test_default_language_is_lazy_and_can_be_overridden_per_value(self):
        with override_settings(DEFAULT_LANGUAGE='fr'), translation.override('it'):
            value = TranslatableText().update(en='English', fr='French')
            self.assertEqual(TranslatableText.DEFAULT, 'fr')
            self.assertEqual(str(value), 'French')
            self.assertNotIn('DEFAULT', vars(value))
            value.DEFAULT = 'en'
            self.assertEqual(str(value), 'English')
