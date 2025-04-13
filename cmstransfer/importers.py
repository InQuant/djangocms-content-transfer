from cms.api import create_page, create_page_content, add_plugin
from cms.models import Page, PageContent, Placeholder
from cmstransfer.items import PageItem, PageContentItem, PlaceholderItem, PluginItem

class PageImporter:
    def __init__(self, page_item: PageItem, parent: Page=None):
        self.page_item = page_item
        self.parent = parent

    def import_page(self) -> Page:
        page = self.create_page(self.page_item)

        for idx, content_item in enumerate(self.page_item.page_contents):
            if idx == 0: continue # already create with create_page ;-)
            self.import_page_content(page, content_item)

        for child_item in self.page_item.pages:
            PageImporter(child_item, parent=page).import_page()

        return page

    def create_page(self, page_item: PageItem) -> Page:
        content = page_item.page_contents[0]
        page = create_page(
            title=content.title,
            template=content.template,
            language=content.language,
            parent=self.parent,
            in_navigation=content.in_navigation,
            reverse_id=page_item.reverse_id,
        )
        return page

    def import_page_content(self, page: Page, content_item: PageContentItem):
        content = create_page_content(
            content_item.language,
            content_item.title,
            page,
            content_item.slug,
            page_title=content_item.page_title,
            meta_description=content_item.meta_description,
            in_navigation=content_item.in_navigation,
            template=content_item.template
        )

        for placeholder_item in content.placeholders:
            self.import_placeholder(content, placeholder_item, content_item.language)

    def import_placeholder(self, content: PageContent, placeholder_item: PlaceholderItem, language: str):
        placeholder = content.get_placeholders().get(slot=placeholder_item.slot)

        for plugin_item in placeholder_item.plugins:
            self.import_plugin(placeholder, plugin_item, language)

    def import_plugin(self, placeholder: Placeholder, plugin_item: PluginItem, language: str, parent=None):
        plugin = add_plugin(
            placeholder,
            plugin_type=plugin_item.plugin_type,
            language=language,
            target=parent,
            **plugin_item.config
        )

        for child_item in plugin_item.children:
            self.import_plugin(placeholder, child_item, language, parent=plugin)

