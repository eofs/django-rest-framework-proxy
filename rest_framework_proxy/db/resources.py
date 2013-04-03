from StringIO import StringIO

from rest_framework.exceptions import UnsupportedMediaType
from rest_framework.serializers import ModelSerializer
from rest_framework.settings import api_settings
from rest_framework.utils.mediatypes import media_type_matches

from rest_framework_proxy.settings import api_proxy_settings
from rest_framework_proxy.exceptions import RemoteModelException


class ResourceOptions(object):
    """
    Hold resource specific options
    """
    def __init__(self, meta):
        self.result_root = getattr(meta, 'result_root', api_proxy_settings.MODEL_RESULT_ROOT)

class ResourceBase(object):
    class Meta(object):
        pass

    _options_class = ResourceOptions

    def __init__(self):
        self.opts = self._options_class(self.Meta)

class RemoteResource(ResourceBase):
    auth = None
    headers = {}
    model = None
    serializer_class = None
    url = None

    def get_authentication(self):
        return self.auth

    def get_headers(self):
        return self.headers

    def get_model(self):
        return self.model

    def get_serializer_class(self):
        serializer_class = self.serializer_class

        if serializer_class is None:
            class DefaultSerializer(ModelSerializer):
                class Meta:
                    model = self.model
            serializer_class = DefaultSerializer

        return serializer_class

    def get_serializer(self, instance=None, data=None):
        serializer_class = self.get_serializer_class()
        return serializer_class(instance=instance, data=data)

    def get_url(self, obj_id=None):
        if self.url is None:
            raise RemoteModelException('URL is required.')

        if obj_id is not None:
            return '%s%s/' % (self.url, obj_id)
        return self.url

    def parse(self, response):
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

    def deserialize(self, data):
        """
        Deserialize response data
        """
        serializer = self.get_serializer(data=data)

        try:
            serializer.is_valid()
        except AttributeError as e:
            raise RemoteModelException(e)

        if serializer.is_valid():
            obj = serializer.object
            pk_field = self.model._meta.pk.attname

            if pk_field in data:
                #Set PK value explicitly as AutoFields are read only in
                # rest_framework
                obj.pk = data[pk_field]
            return obj

        raise RemoteModelException('Could not deserialize data: %s' % serializer.errors)
