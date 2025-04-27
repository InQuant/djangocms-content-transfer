import json

from django import forms
from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import path
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
from cms.forms.fields import PageSelectWidget

from .models import PageExport, PageImport, AliasExport, AliasImport
from .exporters import PageExporter, AliasExporter
from .importers import PageImporter, AliasImporter
from .items import PageItem, AliasItem, TransferItem


# PageExport Admin
# ----------------
class PageExportForm(forms.ModelForm):
    class Meta:
        model = PageExport
        fields = '__all__'
        widgets = {
            'page': PageSelectWidget,
        }
@admin.register(PageExport)
class PageExportAdmin(admin.ModelAdmin):
    #form = PageExportForm
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
    import_action.short_description = "2. Import"

    def update_action(self, obj):
        if not obj.pk:
            return "Save first to enable update."
        url = f'../update/'
        return format_html(
            '<a class="button" href="{}">Update Model Refs of %s Import Data</a>' % self.LABEL, url
        )
    update_action.short_description = "1. Update"

    def update_links_action(self, obj):
        if not obj.pk:
            return "Save first and Import to enable update links."
        url = f'../update-links/'
        return format_html(
            '<a class="button" href="{}">Update Internal Links in Plugins of %s Import Data</a>' % self.LABEL, url
        )
    update_links_action.short_description = "3. Update Links"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:pk>/update/', self.admin_site.admin_view(self.update_view), name=f'{self.LABEL.lower()}-update'),
            path('<int:pk>/import/', self.admin_site.admin_view(self.import_view), name=f'{self.LABEL.lower()}-import'),
            path('<int:pk>/update-links/', self.admin_site.admin_view(self.update_links_view),
                name=f'{self.LABEL.lower()}-update-links'),
        ]
        return custom_urls + urls

    def update_view(self, request, pk):
        if not request.user.is_superuser:
            raise PermissionDenied

        obj = self.get_object(request, pk)
        item = self.item_cls.from_dict(obj.data)
        errors = item.update_model_refs()

        if errors:
            error_html = "<br>".join(f"• {e} not found." for e in errors)
            full_message = mark_safe(f"<strong>{item.type} Model refs with warnings:</strong><br>{error_html}")
            self.message_user(request, full_message, messages.WARNING)

        obj.data = item.asdict()
        obj.save()

        self.message_user(request, f"{item.type} Model Refs successfully updated!", messages.SUCCESS)
        return redirect(f'../')  # back to detail

    def _update_internal_links(self, request, item):
        errors = item.update_internal_links()
        if errors:
            error_html = "<br>".join(f"• {e} not found." for e in errors)
            full_message = mark_safe(f"<strong>{item.type} internal links with warnings:</strong><br>{error_html}")
            self.message_user(request, full_message, messages.WARNING)
        return errors

    def import_view(self, request, pk):
        if not request.user.is_superuser:
            raise PermissionDenied

        obj = self.get_object(request, pk)
        item = self.item_cls.from_dict(obj.data)

        importer = self.get_importer(item, request.user, obj)
        importer.exec_import()

        errors = self._update_internal_links(request, item)
        if errors:
            self.message_user(request, f"{item.type} successfully imported with internal link warnings!",
               messages.SUCCESS)
        else:
            self.message_user(request, f"{item.type} successfully imported!", messages.SUCCESS)

        obj.data = item.asdict()
        obj.save()

        return redirect(f'../')  # back to detail

    def update_links_view(self, request, pk):
        if not request.user.is_superuser:
            raise PermissionDenied

        obj = self.get_object(request, pk)
        item = self.item_cls.from_dict(obj.data)

        errors = self._update_internal_links(request, item)
        if errors:
            self.message_user(request, f"{item.type} has internal link warnings!", messages.SUCCESS)
        else:
            self.message_user(request, f"{item.type}: all links successfully updated!", messages.SUCCESS)

        obj.data = item.asdict()
        obj.save()

        return redirect(f'../')  # back to detail


# PageImport Admin
# ----------------
@admin.register(PageImport)
class PageImportAdmin(ImportActionMixin, admin.ModelAdmin):
    item_cls = PageItem
    LABEL = 'Page'
    list_display = (PageImport, 'parent_page', 'modified_at')
    readonly_fields = ('update_action', 'import_action', 'update_links_action')

    def get_importer(self, item:TransferItem, user, obj):
        return PageImporter(item, user, parent=obj.parent_page)


# AliasImport Admin
# -----------------
@admin.register(AliasImport)
class AliasImportAdmin(ImportActionMixin, admin.ModelAdmin):
    item_cls = AliasItem
    LABEL = 'Alias'
    list_display = (AliasImport, 'modified_at',)
    readonly_fields = ('update_action', 'import_action',)

    def get_importer(self, item:TransferItem, user, obj=None):
        return AliasImporter(item, user)
