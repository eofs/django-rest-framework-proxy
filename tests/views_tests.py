import base64
import requests

from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http.request import QueryDict
from django.test import TestCase
from mock import Mock, patch

from rest_framework_proxy.views import ProxyView
from rest_framework.test import APIRequestFactory
from rest_framework_proxy import settings
from rest_framework_proxy.utils import StreamingMultipart


class ProxyViewTests(TestCase):
    def test_postitional_and_keyword_arguments_passed_through_to_proxy_method(self):
        proxied_http_methods = ['get', 'put', 'post', 'patch', 'delete']
        request = Mock()
        view = ProxyView()

        for http_method in proxied_http_methods:
            with patch.object(ProxyView, 'proxy') as patched_proxy_method:
                handler = getattr(view, http_method)
                handler(request, 42, foo='bar')

            patched_proxy_method.assert_called_once_with(
                request,
                42,
                foo='bar'
            )

    def test_passes_cookies_through_to_request(self):
        request = Mock()
        view = ProxyView()
        view.get_cookies = lambda r: {'test_cookie': 'value'}

        factory = APIRequestFactory()
        request = factory.post('some/url', data={}, cookies={'original_request_cookie': 'I will not get passed'})
        request.content_type = 'application/json'
        request.query_params = ''
        request.data = {}

        with patch('rest_framework_proxy.views.requests.request') as patched_requests:
            with patch.object(view, 'create_response'):
                view.proxy(request)
                args, kwargs = patched_requests.call_args
                request_cookies = kwargs['cookies']
                self.assertEqual(request_cookies, {'test_cookie': 'value'})

    def test_post_file(self):
        view = ProxyView()

        factory = APIRequestFactory()
        request = factory.post('some/url')
        request.content_type = 'multipart/form-data; boundary='\
                               '------------------------f8317b014f42e05a'
        request.query_params = ''

        upload_bstr = b'test binary data'
        upload_file = BytesIO()
        upload_file.write(upload_bstr)
        upload_file.seek(0)
        upload_data = InMemoryUploadedFile(upload_file,
                                           'file',
                                           'test_file.dat',
                                           'application/octet-stream',
                                           len(upload_bstr),
                                           None,
                                           content_type_extra={})

        request.data = QueryDict(mutable=True)
        request.data['file'] = upload_data
        view.get_request_files = lambda r: {'file': upload_data}

        with patch.object(requests.sessions.Session, 'request') as patched_request:
            with patch.object(view, 'create_response'):
                view.proxy(request)
                args, kwargs = patched_request.call_args
                request_data = kwargs['data']
                self.assertEqual(request_data.files, {'file': upload_data})
                self.assertEqual(request_data.data['file'], upload_data)


class ProxyViewHeadersTest(TestCase):

    def get_view(self, custom_settings=None):
        view = ProxyView()
        view.proxy_settings = settings.APISettings(
            custom_settings, settings.DEFAULTS)
        return view

    def test_basic_auth(self):
        username, password = 'abc', 'def'
        view = self.get_view(
            {'AUTH': {'user': username, 'password': password}})
        request = APIRequestFactory().post('')
        headers = view.get_headers(request)

        auth_token = '%s:%s' % (username, password)
        auth_token = base64.b64encode(auth_token.encode('utf-8')).decode()
        expected = 'Basic %s' % auth_token

        self.assertEqual(headers['Authorization'], expected)

    def test_token(self):
        token = 'xyz'
        view = self.get_view({'AUTH': {'token': token}})
        request = APIRequestFactory().post('')
        headers = view.get_headers(request)
        self.assertEqual(headers['Authorization'], token)

    def test_basic_auth_before_token(self):
        username, password = 'abc', 'def'
        view = self.get_view(
            {'AUTH': {'user': username, 'password': password, 'token': 'xyz'}})
        request = APIRequestFactory().post('')
        headers = view.get_headers(request)

        auth_token = '%s:%s' % (username, password)
        auth_token = base64.b64encode(auth_token.encode('utf-8')).decode()
        expected = 'Basic %s' % auth_token

        self.assertEqual(headers['Authorization'], expected)
