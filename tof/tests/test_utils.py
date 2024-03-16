from django.test import SimpleTestCase
from django.utils import translation
from django.utils.crypto import get_random_string

from ..utils import TranslatableText


class TestTranslatableTextIntegration(SimpleTestCase):

    def setUp(self):
        self.test_obj = TranslatableText()
        self.random_english = get_random_string(20)

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

    def test___delitem__(self):
        # class TestSubClass(type(self.test_obj)):

        #     def __delattr__(self, attr, value):
        #         vars(self)[attr] = value
        self.fail('please write test')

    def test___getitem__(self):
        self.fail('please write test')

    def test___str__(self):
        self.fail('please write test')

    def test___repr__(self):
        self.fail('please write test')

    def test___eq__(self):
        self.fail('please write test')

    def test___add__(self):
        self.fail('please write test')

    def test___radd__(self):
        self.fail('please write test')

    def test___len__(self):
        self.fail('please write test')

    def test___bool__(self):
        self.fail('please write test')

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

    def test___iter__(self):
        self.fail('please write test')

    def test_iter(self):
        random_lang = get_random_string(2)
        translation.activate(random_lang)
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
        print(output)
        self.assertEqual(output, expected_output, msg='should match the expected output')

    # @property
    # def iter(self):
    #     langs = dict.fromkeys((self.get_lang(), self.DEFAULT, *(lang for lang in vars(self).keys() if len(lang) == 2)), )
    #     yield from ((lang, value) for lang, value in ((lang, getattr(self, lang, None)) for lang in langs) if value)


    def test_current(self):
        self.fail('please write test')

    def test_get_lang(self):
        self.fail('please write test')
