from modeltranslation.translator import translator, TranslationOptions
from .models import Wine

class NewsTranslationOptions(TranslationOptions):
    fields = ('description',)

translator.register(Wine, NewsTranslationOptions)