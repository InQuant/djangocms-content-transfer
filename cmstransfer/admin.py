import json

from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied

from .models import PageExport, PageImport
from .exporters import PageExporter
from .importers import PageImporter
from .items import PageItem


# PageExport Admin
# ----------------
@admin.register(PageExport)
class PageExportAdmin(admin.ModelAdmin):
    list_display = ('page', 'modified_at')

    def save_model(self, request, obj, form, change):
        # Export and save
        exporter = PageExporter(obj.page, recursive=obj.recursive)
        page_item = exporter.export()
        obj.data = page_item.asdict()
        super().save_model(request, obj, form, change)

    def data_pretty(self, obj):
        json_data = json.dumps(obj.data, indent=2, ensure_ascii=False)
        return format_html(
            '<pre style="white-space: pre-wrap;">{}</pre>',
            json_data
        )
    data_pretty.short_description = "Exported JSON"


# PageImport Admin
# ----------------
@admin.register(PageImport)
class PageImportAdmin(admin.ModelAdmin):
    list_display = ('parent_page', 'modified_at')
    readonly_fields = ('import_page_action',)

    def import_page_action(self, obj):
        if not obj.pk:
            return "Save first to enable import."
        url = f'./{obj.pk}/import-page/'
        return format_html(
            '<a class="button" href="{}">Import Page</a>', url
        )
    import_page_action.short_description = "Import"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:pk>/import-page/', self.admin_site.admin_view(self.import_page_view), name='pageimport-import'),
        ]
        return custom_urls + urls

    def import_page_view(self, request, pk):
        if not request.user.is_superuser:
            raise PermissionDenied

        obj = self.get_object(request, pk)
        page_item = PageItem.from_dict(obj.data)

        importer = PageImporter(page_item, parent=obj.parent_page)
        importer.import_page()

        self.message_user(request, "Page successfully imported!", messages.SUCCESS)
        return redirect(f'../../')  # back to changelist
