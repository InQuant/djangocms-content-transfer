import json
from cms.models import Page
from django.db import models
from djangocms_alias.models import Alias
from .serializers import JsonEncoder

# Transfer Models
#----------------

class Transfer(models.Model):
    data = models.JSONField(encoder=JsonEncoder, blank=True, default=dict)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PageExport(Transfer):
    page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name='+',  # no reverse access via page
        verbose_name='CMS Page.',
        help_text='Select page to export.'
    )
    recursive = models.BooleanField(
        default=False,
        help_text='Exports selected page recursive with all child pages.'
    )

    class Meta:
        verbose_name = 'Page Export'


class PageImport(Transfer):
    parent_page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name='+',  # no reverse access via page
        verbose_name='Parent CMS Page',
        help_text='Select parent page - pages to import are created below.',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Page Import'

    def __str__(self):
        return self.data.get('title') or f'PageImport: {self.id}'

class AliasExport(Transfer):
    alias = models.ForeignKey(
        Alias,
        on_delete=models.CASCADE,
        related_name='+',  # no reverse access via alias
        help_text='Select Alias to export.'
    )

    class Meta:
        verbose_name = 'Alias Export'


class AliasImport(Transfer):
    name = models.CharField(max_length=100, blank=True, default='')

    class Meta:
        verbose_name = 'Alias Import'

    def __str__(self):
        return self.name or f'AliasImport: {self.id}'

    def save(self, *args, **kwargs):
        if not self.name:
            try:
                self.name = self.data['alias_contents'][0]['name']
            except:
                pass
        super().save(*args, **kwargs)
