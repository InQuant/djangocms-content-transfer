from dataclasses import dataclass, field, asdict, fields, is_dataclass
from typing import get_origin, get_args, Type, TypeVar, Dict, Any, List, get_type_hints

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
    config: Dict[str, Any] = field(default_factory=dict)
    children: List['PluginItem'] = field(default_factory=list)

@dataclass
class PlaceholderItem(TransferItem):
    slot: str
    extra_context: Dict[str, Any] = field(default_factory=dict)
    plugins: List[PluginItem] = field(default_factory=list)

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

@dataclass
class PageItem(TransferItem):
    page_id: int
    reverse_id: str = ""
    languages: List[str] = field(default_factory=list)
    pages: List['PageItem'] = field(default_factory=list)
    page_contents: List[PageContentItem] = field(default_factory=list)
