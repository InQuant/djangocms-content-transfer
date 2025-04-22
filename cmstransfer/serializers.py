import datetime
import decimal
import json
import uuid
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.functional import Promise

def get_related_object(value):
    """
    Returns the related field, referenced by the content of a ModelChoiceField.
    """
    try:
        Model = apps.get_model(value["model"])
        relobj = Model.objects.get(pk=value["pk"])
    except (ObjectDoesNotExist, LookupError, TypeError):
        relobj = None
    return relobj

def search_related_object(value):
    """
    try to find a matching model from value field which may have extra lookup fields, e.g. content_code

    value can be:
        {'model': 'filer.image', 'pk': 58, 'sha1': '2e0e6..0'}
        {'model': 'speaker_tool.sessionperson', 'pk': 5, 'name': 'SessionPerson: Max Muster', content_code: '4234-daf'}
    """
    lookup_map = getattr(settings, 'CONTENT_TRANSFER_LOOKUP_KEYS', {})

    mdl_str = value['model']
    mdl = apps.get_model(mdl_str)

    relobj = None
    if mdl_str in lookup_map:
        lookup_key = lookup_map[mdl_str]
        filter = {lookup_key: value.get(lookup_key)}
    else:
        filter = {'pk': value['pk']}
        if mdl_str.startswith('filer.') and 'sha1' in value:
            filter['sha1'] = value['sha1']

    try:
        relobj = mdl.objects.get(**filter)
    except (ObjectDoesNotExist, LookupError, TypeError):
        if mdl_str.startswith('filer.') and 'sha1' in value:
            # try with sha1 only
            filter.pop('pk')
            try:
                mdl.objects.filter(**filter)[0] # to avoid multiple
            except Exception:
                pass # object will be None
    return relobj

class JsonEncoder(json.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time/timedelta,
    decimal types, generators and other basic python objects.
    """

    def default(self, obj):
        if isinstance(obj, models.Model):
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
        # For Date Time string spec, see ECMA 262
        # https://ecma-international.org/ecma-262/5.1/#sec-15.9.1.15
        elif isinstance(obj, Promise):
            return force_str(obj)
        elif isinstance(obj, datetime.datetime):
            representation = obj.isoformat()
            if representation.endswith('+00:00'):
                representation = representation[:-6] + 'Z'
            return representation
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, datetime.time):
            if timezone and timezone.is_aware(obj):
                raise ValueError("JSON can't represent timezone-aware times.")
            representation = obj.isoformat()
            return representation
        elif isinstance(obj, datetime.timedelta):
            return str(obj.total_seconds())
        elif isinstance(obj, decimal.Decimal):
            # Serializers will coerce decimals to strings by default.
            return float(obj)
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, models.query.QuerySet):
            return tuple(obj)
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
        return super().default(obj)
