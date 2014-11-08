from django.test import TestCase

from mock import Mock, patch

from rest_framework_proxy.views import ProxyView


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
