from re import template
from cms.api import create_page, create_page_content, add_plugin
from cms.models import Page, PageContent, Placeholder
from django.core.exceptions import ObjectDoesNotExist
from djangocms_alias.models import Alias, AliasContent, Category
from djangocms_alias.utils import is_versioning_enabled

from .serializers import get_related_object
from .items import PageItem, PageContentItem, PlaceholderItem, PluginItem, AliasItem, AliasContentItem

import logging
logger = logging.getLogger(__name__)

# Mixins
# ------
class PluginMixin:
    def import_plugin(self, placeholder: Placeholder, plugin_item: PluginItem, language: str, parent=None):
        if not '_json' in plugin_item.config:
            # no PlusItem, so we may have to deserialize
            for k, v in plugin_item.config.items():
                plugin_item.config[k] = self.deserialize_value(v, plugin_item.plugin_type, language)

        try:
            plugin = add_plugin(
                placeholder,
                plugin_type=plugin_item.plugin_type,
                language=language,
                target=parent,
                **plugin_item.config
            )
        except Exception as e:
            logger.exception(f'{placeholder.page.get_title()}: cannot import plugin: {plugin_item.asdict()}')
            return
        # save id for update_internal_links
        plugin_item.id = plugin.id

        for child_item in plugin_item.children:
            self.import_plugin(placeholder, child_item, language, parent=plugin)

    def deserialize_value(self, value, plugin_type:str, language:str):
        if isinstance(value, dict) and 'model' in value and 'pk' in value:
            return get_related_object(value)
        else:
            return value

class PlaceholderMixin(PluginMixin):
    def import_placeholder(self, content: PageContent, placeholder_item: PlaceholderItem, language: str):
        try:
            placeholder = content.placeholders.all().get(slot=placeholder_item.slot)
        except ObjectDoesNotExist:
            try:
                placeholder = content.placeholder # alias?
            except AttributeError:
                logger.exception(f'{content.page.get_title()}: cannot import placeholder: {placeholder_item.asdict()}')
                return

        for plugin_item in placeholder_item.plugins:
            self.import_plugin(placeholder, plugin_item, language)


# PageImporter
# ------------
class PageImporter(PlaceholderMixin):
    def __init__(self, page_item: PageItem, user, parent: Page=None):
        self.page_item = page_item
        self.user = user # needed for create_page_content (versioned PageContent)
        self.parent = parent

    def exec_import(self) -> Page:
        page = self.create_page(self.page_item)

        for idx, content_item in enumerate(self.page_item.page_contents):
            # first pagecontent is created with create_page
            pc = page.pagecontent_set.first() if idx == 0 else None
            self.import_page_content(page, content_item, pc)

        for child_item in self.page_item.pages:
            PageImporter(child_item, self.user, parent=page).exec_import()

        return page

    def create_page(self, page_item: PageItem) -> Page:
        language = page_item.page_contents[0].language if len(page_item.page_contents) else page_item.languages[0]
        page = create_page(
            title=page_item.title,
            template=page_item.template,
            language=language,
            parent=self.parent,
            in_navigation=page_item.in_navigation,
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


# AliasImporter
# -------------
class AliasImporter(PlaceholderMixin):
    def __init__(self, alias_item: AliasItem, user):
        self.alias_item = alias_item
        self.user = user # needed for create_alias_content (versioned AliasContent)

    def exec_import(self) -> Alias:
        alias = self.create_alias(self.alias_item)

        for content_item in self.alias_item.alias_contents:
            self.import_alias_content(alias, content_item)

        return alias

    def create_alias(self, alias_item: AliasItem) -> Alias:
        category, created = Category.objects.get_or_create(translations__name=alias_item.category)
        if created:
            category.name = alias_item.category
            category.save()

        return Alias.objects.create(
            category=category
        )

    def import_alias_content(self, alias: Alias, content_item: AliasContentItem):
        content = AliasContent.objects.create(
            alias=alias,
            name=content_item.name,
            language=content_item.language,
        )

        if is_versioning_enabled():
            from djangocms_versioning.models import Version
            Version.objects.create(content=content, created_by=self.user)

        for placeholder_item in content_item.placeholders:
            self.import_placeholder(content, placeholder_item, content_item.language)
