from dataclasses import dataclass, field, asdict, fields
from typing import List, Dict, Type, TypeVar, Any

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
        for f in fields(cls):
            value = data.get(f.name)
            if isinstance(f.type, type) and issubclass(f.type, TransferItem):
                if value:
                    init_data[f.name] = f.type.from_dict(value)
            elif (getattr(f.type, '__origin__', None) is list and
                  hasattr(f.type.__args__[0], 'from_dict')):
                init_data[f.name] = [
                    f.type.__args__[0].from_dict(i) for i in value
                ] if value else []
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
