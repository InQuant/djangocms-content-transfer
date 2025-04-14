from cms.api import create_page, create_page_content, add_plugin
from cms.models import Page, PageContent, Placeholder
from cmstransfer.items import PageItem, PageContentItem, PlaceholderItem, PluginItem
from .serializers import get_related_object

class PageImporter:
    def __init__(self, page_item: PageItem, user, parent: Page=None):
        self.page_item = page_item
        self.user = user # needed for create_page_content (versioned PageContent)
        self.parent = parent

    def import_page(self) -> Page:
        page = self.create_page(self.page_item)

        for idx, content_item in enumerate(self.page_item.page_contents):
            # first pagecontent is created with create_page
            pc = page.pagecontent_set.first() if idx == 0 else None
            self.import_page_content(page, content_item, pc)

        for child_item in self.page_item.pages:
            PageImporter(child_item, parent=page).import_page()

        return page

    def create_page(self, page_item: PageItem) -> Page:
        pc = page_item.page_contents[0]
        page = create_page(
            title=pc.title,
            template=pc.template,
            language=pc.language,
            parent=self.parent,
            in_navigation=pc.in_navigation,
            reverse_id=page_item.reverse_id,
        )
        return page

    def import_page_content(self, page: Page, content_item: PageContentItem, content=None):
        if not content:
            content = create_page_content(
                content_item.language,
                content_item.title,
                page,
                content_item.slug,
                page_title=content_item.page_title,
                meta_description=content_item.meta_description,
                in_navigation=content_item.in_navigation,
                template=content_item.template,
                created_by=self.user
            )

        for placeholder_item in content_item.placeholders:
            self.import_placeholder(content, placeholder_item, content_item.language)

    def import_placeholder(self, content: PageContent, placeholder_item: PlaceholderItem, language: str):
        placeholder = content.get_placeholders().get(slot=placeholder_item.slot)

        for plugin_item in placeholder_item.plugins:
            self.import_plugin(placeholder, plugin_item, language)

    def import_plugin(self, placeholder: Placeholder, plugin_item: PluginItem, language: str, parent=None):
        if not '_json' in plugin_item.config:
            # no PlusItem, so we may have to deserialize
            for k, v in plugin_item.config.items():
                plugin_item.config[k] = self.deserialize_value(v)

        plugin = add_plugin(
            placeholder,
            plugin_type=plugin_item.plugin_type,
            language=language,
            target=parent,
            **plugin_item.config
        )

        for child_item in plugin_item.children:
            self.import_plugin(placeholder, child_item, language, parent=plugin)

    def deserialize_value(self, value):
        if isinstance(value, dict) and 'model' in value and 'pk' in value:
            return get_related_object(value)
        else:
            return value
