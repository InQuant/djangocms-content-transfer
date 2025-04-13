from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder, Deserializer
from django.db import models

def get_related_object(scope, field_name):
    """
    Returns the related field, referenced by the content of a ModelChoiceField.
    """
    try:
        Model = apps.get_model(scope[field_name]["model"])
        relobj = Model.objects.get(pk=scope[field_name]["pk"])
    except (ObjectDoesNotExist, LookupError, TypeError):
        relobj = None
    return relobj


class JsonEncoder(DjangoJSONEncoder):
    """
    subclass that knows how to encode date/time/timedelta,
    decimal types, generators and other basic python objects.
    """

    def default(self, obj):
        from djangocms_alias.models import Alias
        if isinstance(obj, models.Model) or isinstance(obj, Alias):
            return {
                "model": f"{obj._meta.app_label}.{obj._meta.model_name}",
                "pk": obj.pk,
                "name": str(obj)
            }
        elif isinstance(obj, models.query.QuerySet):
            return {
                "model": f"{obj._meta.app_label}.{obj._meta.model_name}",
                "p_keys": list(obj.objs_list("pk", flat=True)),
                "name": str(obj)
            }
        elif isinstance(obj, bytes):
            # Best-effort for binary blobs. See #4187.
            return obj.decode()
        elif hasattr(obj, 'tolist') and callable(obj.tolist):
            # Numpy arrays and array scalars.
            return obj.tolist()
        elif hasattr(obj, '__getitem__'):
            cls = (list if isinstance(obj, (list, tuple)) else dict)
            try:
                return cls(obj)
            except Exception:
                pass
        elif hasattr(obj, '__iter__'):
            return tuple(item for item in obj)
        else:
            return super().default(obj)