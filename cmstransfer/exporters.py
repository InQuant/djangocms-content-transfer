import json
from cms.models import Page, PageContent, Placeholder, CMSPlugin
from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from cmsplus.models import PlusItem
from djangocms_text.models import Text as TextPlugin
from .serializers import JsonEncoder
from .items import PageItem, PageContentItem, PlaceholderItem, PluginItem

class PageExporter:
    def __init__(self, page: Page, recursive=False):
        self.page = page
        self.recursive = recursive
        self.encoder = JsonEncoder()

    def export(self) -> PageItem:
        return self.build_page_item(self.page, self.recursive)

    def build_page_item(self, page: Page, recursive=False) -> PageItem:
        page_item = PageItem(
            type="page",
            page_id=page.id,
            reverse_id=page.reverse_id,
            languages=[lang for lang in page.get_languages()],
        )

        for page_content in PageContent.objects.filter(page=page):
            page_content_item = self.build_page_content_item(page_content)
            page_item.page_contents.append(page_content_item)

        if recursive:
            for child_page in page.get_child_pages():
                child_page_item = self.build_page_item(child_page, recursive)
                page_item.pages.append(child_page_item)

        return page_item

    def build_page_content_item(self, page_content: PageContent) -> PageContentItem:
        content_item = PageContentItem(
            type="pagecontent",
            language=page_content.language,
            title=page_content.title,
            slug=page_content.page.get_slug(page_content.language),
            page_title=page_content.page_title,
            menu_title=page_content.menu_title,
            meta_description=page_content.meta_description,
            in_navigation=page_content.in_navigation,
            template=page_content.template,
        )

        for placeholder in page_content.get_placeholders():
            placeholder_item = self.build_placeholder_item(placeholder, page_content.language)
            content_item.placeholders.append(placeholder_item)

        return content_item

    def build_placeholder_item(self, placeholder: Placeholder, language: str) -> PlaceholderItem:
        placeholder_item = PlaceholderItem(
            type="placeholder",
            slot=placeholder.slot,
            extra_context=placeholder.get_extra_context()
        )

        root_plugin_ids = placeholder.get_plugin_tree_order(language)
        for id in root_plugin_ids:
            plugin = placeholder.get_plugins().get(id=id)
            plugin_item = self.build_plugin_item(plugin)
            placeholder_item.plugins.append(plugin_item)

        return placeholder_item

    def build_plugin_item(self, plugin: CMSPluginBase) -> PluginItem:
        instance, plugin_class = plugin.get_plugin_instance()

        plugin_item = PluginItem(
            type="plugin",
            plugin_type=instance.plugin_type,
            config=self.serialize_instance(instance, plugin_class),
        )

        for child in plugin.get_children().order_by('position'):
            child_item = self.build_plugin_item(child)
            plugin_item.children.append(child_item)

        return plugin_item

    def serialize_instance(self, instance: CMSPlugin, plugin_class: CMSPluginBase):
        """Serializes the instance instance to a dict"""
        config = {}
        if isinstance(instance, PlusItem):
            # handle PlusItem
            config['_json'] = instance.config
        elif isinstance(instance, TextPlugin):
            # handle TextPlugin
            config = {
                'body': instance.body,
                'json': instance.json,
                'rte': 'ckeditor4',
            }
        else:
            # handle other CMSPlugin
            #  instances which have fields, which are not json - serializible may have a serialize method
            if hasattr(instance, 'serialize'):
                config = instance.serialize()
            else:
                # put form fields and values into dict
                plugin_fields = plugin_class.form.base_fields
                for field_name in plugin_fields.keys():
                    if hasattr(instance, field_name):
                        v = getattr(instance, field_name)
                        config[field_name] = self.serialize_value(v)
        return config

    def serialize_value(self, value):
        if isinstance(value, (list, tuple)):
            return [self.serialize_value(v) for v in value]
        elif isinstance(value, dict):
            return {k: self.serialize_value(v) for k, v in value.items()}
        else:
            try:
                return self.encoder.default(value)
            except TypeError:
                return value  # fallback for primitives


    def to_json(self):
        return json.dumps(self.export().asdict(), cls=JsonEncoder, indent=2, ensure_ascii=False)
