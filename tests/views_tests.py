from django.test import TestCase

from mock import Mock, patch

from rest_framework_proxy.views import ProxyView
from rest_framework.test import APIRequestFactory


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
