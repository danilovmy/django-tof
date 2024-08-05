from django.contrib import admin

from .models import Vintage, Wine, Winery

class WineInline(admin.TabularInline):
    model = Wine

class VintageInline(admin.TabularInline):
    model = Vintage


@admin.register(Winery)
class WineryAdmin(admin.ModelAdmin):
    """Example translatable field №3

    This class is example where you can see Tabular inline

    Attributes:
        list_display: [description]
        search_fields: [description]
        inlines
    """
    list_display = ('title', 'description', 'sort')
    search_fields = ('title', )
    inlines = (WineInline, )


@admin.register(Wine)
class WineAdmin(admin.ModelAdmin):
    """Example translatable field №2

    This class is example where translatable field save values to all added languages

    Attributes:
        list_display: [description]
        search_fields: [description]
        form: [description]
    """
    list_display = ('title', 'description', 'active', 'sort')
    search_fields = ('title', )
    only_current_lang = ('description', )
    inlines = (VintageInline, )


@admin.register(Vintage)
class VintageAdmin(admin.ModelAdmin):
    """Example translatable field №1

    This class is example where translatable field save value only in current language

    Attributes:
        list_display: [description]
    """
    list_display = search_fields = ('wine__title', 'year', 'description')

    def wine__title(self, obj, *args, **kwargs):
        return obj.wine.title

    def get_queryset(self, request):
        return super().get_queryset(request)
