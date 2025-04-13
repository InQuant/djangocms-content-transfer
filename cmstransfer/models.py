from cms.models import Page
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder

# Transfer Models
#----------------

class Transfer(models.Model):
    data = models.JSONField(encoder=DjangoJSONEncoder)
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

    class Meta:
        verbose_name = 'Page Export'


class PageImport(Transfer):
    parent_page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name='+',  # no reverse access via page
        verbose_name='Parent CMS Page',
        help_text='Select parent page - pages to import are created below.'
    )

    class Meta:
        verbose_name = 'Page Import'
