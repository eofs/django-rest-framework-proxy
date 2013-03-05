import requests

from StringIO import StringIO
from django.db.models import query
from django.core.exceptions import FieldError
from django.db.models.sql.constants import ORDER_PATTERN
from rest_framework.settings import api_settings
from rest_framework.utils.mediatypes import media_type_matches
from rest_framework.exceptions import UnsupportedMediaType
from rest_framework.serializers import ModelSerializer

from rest_framework_proxy.settings import api_proxy_settings
from rest_framework_proxy.exceptions import ProxyException, ProxyRequestException


class Query(object):
    """
    Limited version of Django's Query object
    """
    def __init__(self):
        self.default_ordering = []
        self.order_by = []
        self.filters = {}
        self.low_mark, self.high_mark = 0, None
        self.page, self.page_size = None, None

    def add_ordering(self, *ordering):
        """
        Adds items from the 'ordering' sequence to the query's "order by"
        clause. These items are either field names (not column names) --
        possibly with a direction prefix ('-' or '?') -- or ordinals,
        corresponding to column positions in the 'select' list.

        If 'ordering' is empty, all ordering is cleared from the query.
        """
        errors = []
        for item in ordering:
            if not ORDER_PATTERN.match(item):
                errors.append(item)
        if errors:
            raise FieldError('Invalid order_by arguments: %s' % errors)
        if ordering:
            self.order_by.extend(ordering)
        else:
            self.default_ordering = False

    def can_filter(self):
        return not self.low_mark and self.high_mark is None

    def clear_ordering(self):
        self.order_by = []

    def clone(self):
        return self

    def filter(self, *args, **kwargs):
        self.filters.update(kwargs)

    def set_limits(self, low=None, high=None):
        if high is not None:
            if self.high_mark is not None:
                self.high_mark = min(self.high_mark, self.low_mark + high)
            else:
                self.high_mark = self.low_mark + high

        if low is not None:
            if self.high_mark is not None:
                self.low_mark = min(self.high_mark, self.low_mark + low)
            else:
                self.low_mark = self.low_mark + low

    def set_page(self, page, size=None):
        self.page = page
        self.page_size = size

    @property
    def parameters(self):
        parameters = {}

        # Filters
        parameters.update(self.filters)

        # Ordering
        order_param = 'order'
        parameters.update({
            order_param: self.order_by
        })

        PARAM_MAP = api_proxy_settings.MODEL_PARAM_MAP

        # Pagination
        if self.page:
            parameters.update({
                PARAM_MAP.get('PAGE'): self.page
            })

        if self.page_size:
            parameters.update({
                PARAM_MAP.get('PAGE_SIZE'): self.page_size
            })

        # Slicing
        if self.low_mark or self.high_mark:
            parameters.update({
                PARAM_MAP.get('OFFSET'): self.low_mark,
                PARAM_MAP.get('LIMIT'): self.high_mark
            })

        return parameters

class ProxyQuerySet(query.QuerySet):
    """
    QuerySet to access data from remote
    """
    def __init__(self, model=None, query=None, using=None):
        self.model = model
        self._db = None # Nope, no database here
        self.query = query or Query()
        self._result_cache = None
        self._iter = None
        self._sticky_filter = False
        self._for_write = False
        self._prefetch_related_lookups = []
        self._prefetch_done = False

    def iterator(self):
        """
        Apply this QuerySet to the remote
        """
        response = requests.get(self.model.get_resource_url(),
                                headers=self.model.get_resource_headers(),
                                params=self.query.parameters,
                                auth=(api_proxy_settings.AUTH['user'],
                                      api_proxy_settings.AUTH['password']))

        status = response.status_code
        if status >= 400:
            raise ProxyRequestException(status, response.reason)

        from_field = api_proxy_settings.MODEL_LIST_FROM_FIELD
        try:
            # Try to set value from model
            from_field = self.model.get_resource_list_from_field()
        except AttributeError:
            pass

        data = self._parse(response)
        if from_field:
            """
            Get objects from specified field instead using complete result as is.
            """
            results = data.get(from_field, None)
            if results:
                for obj in data.get(from_field):
                    yield self._deserialize(obj)
            return
        yield self._deserialize(data)

    def filter(self, *args, **kwargs):
        if args or kwargs:
            assert self.query.can_filter(), \
                    "Cannot filter a query once a slice has been taken."
        clone = self._clone()
        clone.query.filter(*args, **kwargs)
        return clone

    def page(self, page, size=None):
        clone = self._clone()
        clone.query.set_page(page, size)
        return clone

    def get(self, *args, **kwargs):
        """
        Performs the query and returns a single object matching the given
        keyword arguments.
        """
        # Default field
        default_field  = self.model._meta.pk.attname

        # Lookup for field to use
        field = None
        for item in ('id', 'pk', default_field):
            if item in kwargs.keys():
                field = item
                break

        id = kwargs.get(field)
        if id is None:
            raise ProxyException('ID is required. Cannot fetch single item without it.')

        # Remove ID field from copy of kwargs
        filtered_kwargs = dict(kwargs)
        del filtered_kwargs[field]

        # Set filters
        clone = self.filter(*args, **filtered_kwargs)
        if self.query.can_filter():
            clone = clone.order_by()

        URL = '%s%s' % (self.model.get_resource_url(), id)

        response = requests.get(URL,
                                headers=self.model.get_resource_headers(),
                                params=clone.query.parameters,
                                auth=(api_proxy_settings.AUTH['user'],
                                      api_proxy_settings.AUTH['password']))

        status = response.status_code
        if status >= 400:
            if status == 404:
                raise self.model.DoesNotExist(
                    "%s matching query does not exist. "
                    "Lookup parameters were %s" %
                    (self.model._meta.object_name, kwargs))
            raise ProxyRequestException(status, response.reason)

        data = self._parse(response)
        return self._deserialize(data)

    def _clone(self, klass=None, setup=False, **kwargs):
        if klass is None:
            klass = self.__class__
        query = self.query.clone()
        if self._sticky_filter:
            query.filter_is_sticky = True
        c = klass(model=self.model, query=query)
        c.__dict__.update(kwargs)
        if setup and hasattr(c, '_setup_query'):
            c._setup_query()
        return c

    def _parse(self, response):
        """
        Parse response and return data
        """
        stream = StringIO(response.content)
        content_type = response.headers.get('content-type', None)

        if stream is None or content_type is None:
            return

        parsers = [parser() for parser in api_settings.DEFAULT_PARSER_CLASSES]
        parser = None
        for item in parsers:
            if media_type_matches(item.media_type, content_type):
                parser = item

        if not parser:
            raise UnsupportedMediaType(content_type)

        parsed = parser.parse(stream, content_type)

        # Parser classes may return the raw data, or a
        # DataAndFiles object. Return only data.
        try:
            return parsed.data
        except AttributeError:
            return parsed

    def _deserialize(self, data):
        try:
            serializer_class = self.model.get_resource_serializer()
        except AttributeError:
            serializer_class = None

        if not serializer_class:
            class DefaultSerializer(ModelSerializer):
                class Meta:
                    model = self.model
            serializer_class = DefaultSerializer

        serializer = serializer_class(data=data)
        if serializer.is_valid():
            return serializer.object
        raise ProxyException('Could not deserialize data.')
