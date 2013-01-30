import base64
import json
import requests

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

    def get_request_url(self, request):
        path = self.get_source_path()
        url = '%s/%s' % (self.get_proxy_host(), path)
        return url

    def get_request_params(self, request):
        if request.QUERY_PARAMS:
            return request.QUERY_PARAMS.dict()
        return {}

    def get_request_data(self, request):
        data = {}
        if request.DATA:
            data.update(requests.DATA.dict())
        return data

    def get_request_files(self, request):
        files = {}
        if request.FILES:
            for field, content in request.FILES.items():
                files[field] = content.read()
        return files

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

    def proxy(self, request):
        url = self.get_request_url(request)
        params = self.get_request_params(request)
        data = self.get_request_data(request)
        files = self.get_request_files(request)
        headers = self.get_headers(request)


        response = requests.request(request.method, url,
                params=params,
                data=data,
                files=files,
                headers=headers)

        if response.status_code != requests.codes.ok:
            body = {
                'detail': 'Proxy error',
                'code': response.status_code,
                'msg': response.reason,
            }
        else:
            body = json.loads(response.text)
        status = response.status_code

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
