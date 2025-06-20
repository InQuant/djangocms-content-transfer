from cms.models import Page
from dataclasses import dataclass, field, asdict, fields, is_dataclass
from re import I
from typing import get_origin, get_args, Type, TypeVar, Dict, Any, List, get_type_hints
from .serializers import search_related_objects, get_object_by_abs_url

from django.core.exceptions import ObjectDoesNotExist
from cmsplus.models import PlusItem

import json

T = TypeVar('T', bound='TransferItem')

@dataclass
class TransferItem:
    """Core class for all items (Page, Placeholder, Alias) to be ex-/imported
    """
    type: str

    class Meta:
        verbose_name = "Transfer Item"

    def __str__(self):
        return f"{self.Meta.verbose_name}: {self.type}"

    def collect_plugins(self) -> List['PluginItem']:
        return []

    def asdict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        init_data = {}

        # Resolve Types incl. ForwardRefs like: List['PluginItem']
        type_hints = get_type_hints(cls)

        for f in fields(cls):
            value = data.get(f.name)
            field_type = type_hints[f.name]  # not f.type! which is "'Plugin'"
            origin = get_origin(field_type)

            if is_dataclass(field_type) and issubclass(field_type, TransferItem):
                if value:
                    init_data[f.name] = field_type.from_dict(value)

            elif origin is list:
                item_type = get_args(field_type)[0]
                if hasattr(item_type, 'from_dict'):
                    init_data[f.name] = [item_type.from_dict(i) for i in value] if value else []
                else:
                    init_data[f.name] = value

            else:
                init_data[f.name] = value

        return cls(**init_data)


@dataclass
class PluginItem(TransferItem):
    plugin_type: str
    id : int = -1
    config: Dict[str, Any] = field(default_factory=dict)
    children: List['PluginItem'] = field(default_factory=list)

    def collect_plugins(self) -> List['PluginItem']:
        plugins = [self]
        for child in self.children:
            plugins.extend(child.collect_plugins())
        return plugins

    def update_model_refs(self) -> list[str]:
        """queries all model refs in config and updates pks. 

        Returns:
            list[str]: errors - list of model_values where no db obj can be found
        """
        errors = []
        config = self.config if not '_json' in self.config else self.config.get('_json')
        mdl_values = [v for v in config.values() if isinstance(v, dict) and 'model' in v]
        for mdl_value in mdl_values:
            objs = search_related_objects(mdl_value, self.plugin_type)
            if not objs:
                errors.append(mdl_value.copy())
            elif 'pk' in mdl_value:
                obj = objs[0]
                mdl_value['pk'] = obj.pk if obj else None
            else:
                mdl_value['p_keys'] = [obj.pk for obj in objs]

        return errors

    def update_internal_links(self) -> list[str]:
        """queries all internal links in config and updates replaces abs_url with pk.
        Must not be called befor import or self.plugin must exist

        Returns:
            list[str]: errors - list of model_values where no db obj can be found
        """
        errors = []
        if not hasattr(self, 'config') or not self.config.get('_json'):
            return errors  # internal links only exists for PlusItems

        if self.id == -1:
            # raise ImportError(f'must not be called before import or self.id must exist. ({self})!')
            return errors

        try:
            backup_page = Page.objects.get(reverse_id='error-404')
        except ObjectDoesNotExist as e:
            raise ImportError(f'backup page with reverse_id: "error-404" not found!')

        try:
            plugin = PlusItem.objects.get(id=self.id)
        except ObjectDoesNotExist as e:
            # plugin no longer exists, so nothing to do
            return errors

        config = plugin.config
        link_items = [(k, v) for k, v in config.items() if isinstance(v, dict) and 'internal_link' in v]
        for key, link_value in link_items:
            # import values must be gotten from import item config
            import_link_value = self.config['_json'][key]
            mdl_str, abs_url = import_link_value['internal_link'].split(':')
            if not abs_url.startswith('/'):
                continue # update already done
            obj = get_object_by_abs_url(mdl_str, abs_url)
            if not obj:
                errors.append(import_link_value.copy())
                link_value['internal_link'] = f'cms.page:{backup_page.pk}'
                # create data attribute with absolute url for later fixing
                plugin.config['attributes'][f'data-link-{key}'] = json.dumps(import_link_value)
            else:
                link_value['internal_link'] = f'{mdl_str}:{obj.pk}'
                # also update import_link_value to avoid fixing again
                import_link_value['internal_link'] = f'{mdl_str}:{obj.pk}'
            plugin.save()

        return errors


@dataclass
class PlaceholderItem(TransferItem):
    slot: str
    extra_context: Dict[str, Any] = field(default_factory=dict)
    plugins: List[PluginItem] = field(default_factory=list)

    def collect_plugins(self) -> List[PluginItem]:
        plugins = []
        for plugin in self.plugins:
            plugins.extend(plugin.collect_plugins())
        return plugins

@dataclass
class PageContentItem(TransferItem):
    language: str
    title: str
    slug: str
    page_title: str = ""
    menu_title: str = ""
    meta_description: str = ""
    in_navigation: bool = True
    template: str = ""
    placeholders: List[PlaceholderItem] = field(default_factory=list)

    def collect_plugins(self) -> List[PluginItem]:
        plugins = []
        for placeholder in self.placeholders:
            plugins.extend(placeholder.collect_plugins())
        return plugins

@dataclass
class PageItem(TransferItem):
    page_id: int
    reverse_id: str = ""
    title: str = ""
    template: str = ""
    in_navigation: bool = True
    languages: List[str] = field(default_factory=list)
    page_contents: List[PageContentItem] = field(default_factory=list)
    pages: List['PageItem'] = field(default_factory=list)

    def collect_plugins(self) -> List[PluginItem]:
        plugins = []
        for content in self.page_contents:
            plugins.extend(content.collect_plugins())
        for subpage in self.pages:
            plugins.extend(subpage.collect_plugins())
        return plugins

    def update_model_refs(self) -> list[str]:
        """collects all plugins and updates there model refs.
        """
        errors = []
        for plugin in self.collect_plugins():
            errors.extend(plugin.update_model_refs())
        return errors

    def update_internal_links(self) -> list[str]:
        """collects all plugins and updates there internal links.
        """
        errors = []
        for plugin in self.collect_plugins():
            errors.extend(plugin.update_internal_links())
        return errors

@dataclass
class AliasContentItem(TransferItem):
    language: str
    name: str
    template: str = ""
    placeholders: List[PlaceholderItem] = field(default_factory=list)

    def collect_plugins(self) -> List[PluginItem]:
        plugins = []
        for placeholder in self.placeholders:
            plugins.extend(placeholder.collect_plugins())
        return plugins

@dataclass
class AliasItem(TransferItem):
    alias_id: int
    category: str
    languages: List[str] = field(default_factory=list)
    alias_contents: List[AliasContentItem] = field(default_factory=list)

    def collect_plugins(self) -> List[PluginItem]:
        plugins = []
        for content in self.alias_contents:
            plugins.extend(content.collect_plugins())
        return plugins

    def update_model_refs(self) -> list[str]:
        """collects all plugins and updates there model refs.
        """
        errors = []
        for plugin in self.collect_plugins():
            errors.extend(plugin.update_model_refs())
        return errors

    def update_internal_links(self) -> list[str]:
        """collects all plugins and updates there internal links.
        """
        errors = []
        for plugin in self.collect_plugins():
            errors.extend(plugin.update_internal_links())
        return errors
