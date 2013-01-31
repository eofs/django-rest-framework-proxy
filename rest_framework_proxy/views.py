import base64
import requests

from StringIO import StringIO
from requests.exceptions import ConnectionError, SSLError, Timeout
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.utils.mediatypes import media_type_matches
from rest_framework.exceptions import UnsupportedMediaType

from rest_framework_proxy.settings import api_proxy_settings


class BaseProxyView(APIView):
    proxy_settings = api_proxy_settings
    proxy_host = None
    source = None


class ProxyView(BaseProxyView):
    """
    Proxy view
    """
    def get_proxy_host(self):
        return self.proxy_host or self.proxy_settings.HOST

    def get_source_path(self):
        return self.source % self.kwargs

    def get_request_url(self, request):
        path = self.get_source_path()
        url = '%s/%s' % (self.get_proxy_host(), path)
        return url

    def get_request_params(self, request):
        if request.QUERY_PARAMS:
            proxy_params = {}
            for key, value in request.QUERY_PARAMS.items():
                if key not in self.proxy_settings.DISALLOWED_PARAMS:
                    proxy_params[key] = value
            return proxy_params
        return {}

    def get_request_data(self, request):
        data = {}
        if request.DATA:
            data.update(request.DATA.dict())
        return data

    def get_request_files(self, request):
        files = {}
        if request.FILES:
            for field, content in request.FILES.items():
                files[field] = content.read()
        return files

    def get_default_headers(self, request):
        return {
            'Accept': request.META.get('HTTP_ACCEPT', self.proxy_settings.DEFAULT_HTTP_ACCEPT),
            'Accept-Language': request.META.get('HTTP_ACCEPT-LANGUAGE', self.proxy_settings.DEFAULT_HTTP_ACCEPT_LANGUAGE),
            'Content_Type': request.META.get('HTTP_CONTENT_TYPE', self.proxy_settings.DEFAULT_HTTP_CONTENT_TYPE),
        }

    def get_headers(self, request):
        #import re
        #regex = re.compile('^HTTP_')
        #request_headers = dict((regex.sub('', header), value) for (header, value) in request.META.items() if header.startswith('HTTP_'))
        headers = self.get_default_headers(request)

        # Translate Accept HTTP field
        accept_maps = self.proxy_settings.ACCEPT_MAPS
        for old, new in accept_maps.items():
           headers['Accept'] = headers['Accept'].replace(old, new)

        username = self.proxy_settings.AUTH['user']
        password = self.proxy_settings.AUTH['password']
        if username and password:
            base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
            headers['Authorization'] = 'Basic %s' % base64string
        return headers

    def parse_proxy_response(self, response):
        """
        Modified version of rest_framework.request.Request._parse(self)
        """
        parsers = self.get_parsers()
        stream = StringIO(response._content)
        content_type = response.headers.get('content-type', None)

        if stream is None or content_type is None:
            return None

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

    def proxy(self, request):
        url = self.get_request_url(request)
        params = self.get_request_params(request)
        data = self.get_request_data(request)
        files = self.get_request_files(request)
        headers = self.get_headers(request)

        response = None
        body = {}
        status = requests.status_codes.codes.ok

        try:
            response = requests.request(request.method, url,
                    params=params,
                    data=data,
                    files=files,
                    headers=headers,
                    timeout=self.proxy_settings.TIMEOUT)
        except (ConnectionError, SSLError):
            status = requests.status_codes.codes.bad_gateway
            body = {
                'code': status,
                'error': 'Bad gateway',
            }
        except (Timeout):
            status = requests.status_codes.codes.gateway_timeout
            body = {
                'code': status,
                'error': 'Gateway timed out',
            }

        if response is not None:
            status = response.status_code
            if response.status_code >= 400:
                body = {
                    'code': status,
                    'error': response.reason,
                }
            else:
                body = self.parse_proxy_response(response)

        return Response(body, status)

    def get(self, request, *args, **kwargs):
        return self.proxy(request)

    def put(self, request, *args, **kwargs):
        return self.proxy(request)

    def post(self, request, *args, **kwargs):
        return self.proxy(request)

    def patch(self, request, *args, **kwargs):
        return self.proxy(request)

    def delete(self, request, *args, **kwargs):
        return self.proxy(request)
