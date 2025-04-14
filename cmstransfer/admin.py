import json

from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied

from .models import PageExport, PageImport, AliasExport, AliasImport
from .exporters import PageExporter, AliasExporter
from .importers import PageImporter, AliasImporter
from .items import PageItem, AliasItem

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


# AliasExport Admin
# -----------------
@admin.register(AliasExport)
class AliasExportAdmin(admin.ModelAdmin):
    list_display = ('alias', 'modified_at')

    def save_model(self, request, obj, form, change):
        # Export and save
        exporter = AliasExporter(obj.alias)
        alias_item = exporter.export()
        obj.data = alias_item.asdict()
        super().save_model(request, obj, form, change)


# Import Mixin
# ------------
class ImportActionMixin:
    def import_action(self, obj):
        if not obj.pk:
            return "Save first to enable import."
        url = f'../import/'
        return format_html(
            '<a class="button" href="{}">Import %s</a>' % self.LABEL, url
        )
    import_action.short_description = "Import"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:pk>/import/', self.admin_site.admin_view(self.import_view), name=f'{self.LABEL.lower()}-import'),
        ]
        return custom_urls + urls


# PageImport Admin
# ----------------
@admin.register(PageImport)
class PageImportAdmin(ImportActionMixin, admin.ModelAdmin):
    LABEL = 'Page'
    list_display = ('parent_page', 'modified_at')
    readonly_fields = ('import_action',)

    def import_view(self, request, pk):
        if not request.user.is_superuser:
            raise PermissionDenied

        obj = self.get_object(request, pk)
        page_item = PageItem.from_dict(obj.data)

        importer = PageImporter(page_item, request.user, parent=obj.parent_page)
        importer.import_page()

        self.message_user(request, "Page successfully imported!", messages.SUCCESS)
        return redirect(f'../../')  # back to changelist


# AliasImport Admin
# -----------------
@admin.register(AliasImport)
class AliasImportAdmin(ImportActionMixin, admin.ModelAdmin):
    LABEL = 'Alias'
    list_display = (AliasImport, 'modified_at',)
    readonly_fields = ('import_action',)

    def import_view(self, request, pk):
        if not request.user.is_superuser:
            raise PermissionDenied

        obj = self.get_object(request, pk)
        alias_item = AliasItem.from_dict(obj.data)

        importer = AliasImporter(alias_item, request.user)
        importer.import_alias()

        self.message_user(request, "Alias successfully imported!", messages.SUCCESS)
        return redirect(f'../../')  # back to changelist
