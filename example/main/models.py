from django.db import models
from django.utils.translation import gettext_lazy as _


class Winery(models.Model):
    class Meta:
        verbose_name = _('Winery')
        verbose_name_plural = _('Winery-plural')
        ordering = ('sort', )

    title = models.CharField(_('Title'), max_length=250, default='', blank=True, null=False)
    description = models.TextField(_('Description'), null=True, blank=True)
    sort = models.IntegerField(_('Sort'), default=0, blank=True, null=True)


class Wine(models.Model):
    class Meta:
        verbose_name = _('wine')
        verbose_name_plural = _('wine-plural')
        ordering = ('sort', )

    title = models.CharField(_('Title'), max_length=250, default='', blank=True, null=False)
    description = models.TextField(_('Description'), null=True, blank=True)
    active = models.BooleanField(_('Active'), default=False)
    sort = models.IntegerField(_('Sort'), default=0, blank=True, null=True)

    winery = models.ForeignKey(Winery, related_name='wines', on_delete=models.CASCADE)
    temperature_from = models.FloatField(_('Temperature_from'), help_text=_('in ° C'), null=True, blank=True)
    temperature_to = models.FloatField(_('Temperature_to'), help_text=_('in ° C'), null=True, blank=True)


class Vintage(models.Model):
    wine = models.ForeignKey(Wine, related_name='vintages', on_delete=models.CASCADE)
    year = models.IntegerField(_('Year'), default=0)
    description = models.TextField(_('Description'), null=True, blank=True)
