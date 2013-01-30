import base64
import urllib2
import json

from rest_framework.response import Response
from rest_framework.views import APIView

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

    def create_request_url(self, request):
        path = self.get_source_path()
        url = '%s/%s' % (self.get_proxy_host(), path)
        if request.QUERY_PARAMS:
            # Do not pass 'format' parameter as we are forcing Accept value
            params = request.QUERY_PARAMS.copy()
            del params['format']
            url += '?' + params.urlencode()
        return url

    def create_request(self, url, body=None, headers={}):
        return urllib2.Request(url, body, headers)

    def get_proxy_request(self, request):
        url = self.create_request_url(request)
        headers = self.get_headers(request)
        return self.create_request(url, headers=headers)

    def get_default_headers(self):
        return {
            'Accept': 'application/json',
        }

    def get_headers(self, request):
        headers = self.get_default_headers()

        username = self.proxy_settings.AUTH['user']
        password = self.proxy_settings.AUTH['password']
        if username and password:
            base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
            headers['Authorization'] = 'Basic %s' % base64string
        return headers

    def get(self, request, *args, **kwargs):
        request = self.get_proxy_request(request)
        try:
            response = urllib2.urlopen(request, timeout=self.proxy_settings.TIMEOUT)
            body = json.loads(response.read())
        except urllib2.HTTPError, e:
            body = {
                'detail': 'Proxy error',
                'code': e.code,
                'msg': e.msg,
            }
        return Response(body)

    def put(self, request, *args, **kwargs):
        # TODO Handling
        return Response({'type': 'PUT'})

    def post(self, request, *args, **kwargs):
        # TODO Handling
        return Response({'type': 'POST'})

    def patch(self, request, *args, **kwargs):
        # TODO Handling
        return Response({'type': 'PATCH'})

    def delete(self, request, *args, **kwargs):
        # TODO Handling
        return Response({'type': 'DELETE'})
