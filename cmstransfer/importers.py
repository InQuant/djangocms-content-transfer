from re import template
from cms.api import create_page, create_page_content, add_plugin
from cms.models import Page, PageContent, Placeholder
from django.core.exceptions import ObjectDoesNotExist
from djangocms_alias.models import Alias, AliasContent, Category
from djangocms_alias.utils import is_versioning_enabled

from .serializers import get_related_object
from .items import PageItem, PageContentItem, PlaceholderItem, PluginItem, AliasItem, AliasContentItem

# Mixins
# ------
class PluginMixin:
    def import_plugin(self, placeholder: Placeholder, plugin_item: PluginItem, language: str, parent=None):
        if not '_json' in plugin_item.config:
            # no PlusItem, so we may have to deserialize
            for k, v in plugin_item.config.items():
                plugin_item.config[k] = self.deserialize_value(v, plugin_item.plugin_type, language)

        plugin = add_plugin(
            placeholder,
            plugin_type=plugin_item.plugin_type,
            language=language,
            target=parent,
            **plugin_item.config
        )

        for child_item in plugin_item.children:
            self.import_plugin(placeholder, child_item, language, parent=plugin)

    def deserialize_value(self, value, plugin_type:str, language:str):
        if isinstance(value, dict) and 'model' in value and 'pk' in value:
            obj = get_related_object(value)
            if obj == None and plugin_type == 'Alias':
                obj = self.get_alias_obj_by_name(value, language)
            return obj
        else:
            return value

    def get_alias_obj_by_name(self, value, language):
        try:
            obj = Alias.objects.get(contents__name=value['name'], contents__language=language)
        except (ObjectDoesNotExist, LookupError, TypeError):
            obj = None
        return obj


class PlaceholderMixin(PluginMixin):
    def import_placeholder(self, content: PageContent, placeholder_item: PlaceholderItem, language: str):
        try:
            placeholder = content.placeholders.all().get(slot=placeholder_item.slot)
        except ObjectDoesNotExist:
            placeholder = content.placeholder # alias?

        for plugin_item in placeholder_item.plugins:
            self.import_plugin(placeholder, plugin_item, language)


# PageImporter
# ------------
class PageImporter(PlaceholderMixin):
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
            PageImporter(child_item, self.user, parent=page).import_page()

        return page

    def create_page(self, page_item: PageItem) -> Page:
        language = page_item.page_contents[0] if len(page_item.page_contents) else page_item.languages[0]
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

    def import_alias(self) -> Alias:
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
