Django Rest Framework Proxy
====================

[![PyPI version](https://badge.fury.io/py/django-rest-framework-proxy.svg)](http://badge.fury.io/py/django-rest-framework-proxy)
[![Build Status](https://travis-ci.org/eofs/django-rest-framework-proxy.svg?branch=master)](https://travis-ci.org/eofs/django-rest-framework-proxy)
[![Coverage Status](https://coveralls.io/repos/eofs/django-rest-framework-proxy/badge.png?branch=master)](https://coveralls.io/r/eofs/django-rest-framework-proxy?branch=master)

Provides views to redirect incoming request to another API server.

**Features:**

* Masquerade paths
* HTTP Basic Auth (between your API and backend API)
* Token Auth
* Supported methods: GET/POST/PUT/PATCH
* File uploads

**TODO:**
* Pass auth information from original client to backend API

#Installation#

```bash
$ pip install django-rest-framework-proxy
```

#Usage#
There are couple of ways to use proxies. You can either use provided views as is or subclass them.

## Settings ##
```python
# settings.py
REST_PROXY = {
    'HOST': 'https://api.example.com',
    'AUTH': {
        'user': 'myuser',
        'password': 'mypassword',
        # Or alternatively:
        'token': 'Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b',
    },
}
```


## Simple way ##
```python
# urls.py
from rest_framework_proxy.views import ProxyView

# Basic
url(r'^item/$', ProxyView.as_view(source='items/'), name='item-list'),

# With captured URL parameters
url(r'^item/(?P<pk>[0-9]+)$', ProxyView.as_view(source='items/%(pk)s'), name='item-detail'),
```
## Complex way ##
```python
# views.py
from rest_framework_proxy.views import ProxyView

class ItemListProxy(ProxyView):
  """
  List of items
  """
  source = 'items/'

class ItemDetailProxy(ProxyView):
  """
  Item detail
  """
  source = 'items/%(pk)s'

```
```python
# urls.py
from views import ProxyListView, ProxyDetailView

url(r'^item/$', ProxyListView.as_view(), name='item-list'),
url(r'^item/(?P<pk>[0-9]+)$', ProxyDetailView.as_view(), name='item-detail'),
```

# Settings #
<table>
    <thead>
        <tr>
            <td>Setting</td>
            <td>Default</td>
            <td>Comment</td>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>HOST</td>
            <td><code>None</code></td>
            <td>Proxy request to this host (e.g. https://example.com/api/).</td>
        </tr>
        <tr>
            <td>AUTH</td>
            <td><code>{'user': None, 'password': None, 'token': None}</code></td>
            <td>Proxy requests using HTTP Basic or Token Authentication.
            Token is only used if user &amp; password are not provided.</td>
        </tr>
        <tr>
            <td>TIMEOUT</td>
            <td><code>None</code></td>
            <td>Timeout value for proxy requests.</td>
        </tr>
        <tr>
            <td>ACCEPT_MAPS</td>
            <td><code>{'text/html': 'application/json'}</code></td>
            <td>Modify Accept-headers before proxying them. You can use this to disallow certain types. By default <code>text/html</code> is translated to return JSON data.</td>
        </tr>
        <tr>
            <td>DISALLOWED_PARAMS</td>
            <td><code>('format',)</code></td>
            <td>Remove defined query parameters from proxy request.</td>
        </tr>
    </tbody>
</table>

# SSL Verification #
By default, `django-rest-framework-proxy` will verify the SSL certificates when proxying requests, defaulting
to security. In some cases, it may be desirable to not verify SSL certificates. This setting can be modified
by overriding the `VERIFY_SSL` value in the `REST_PROXY` settings.

Additionally, one may set the `verify_proxy` settings on their proxy class:

```python
# views.py
from rest_framework_proxy.views import ProxyView

class ItemListProxy(ProxyView):
  """
  List of items
  """
  source = 'items/'
  verify_ssl = False

```

Finally, if there is complex business logic needed to determine if one should verify SSL, then
you can override the `get_verify_ssl()` method on your proxy view class:

```python
# views.py
from rest_framework_proxy.views import ProxyView

class ItemListProxy(ProxyView):
  """
  List of items
  """
  source = 'items/'

  def get_verify_ssl(self, request):
    host = self.get_proxy_host(request)
    if host.startswith('intranet.'):
      return True
    return False

```

# Permissions #
You can limit access by using Permission classes and custom Views.
See http://django-rest-framework.org/api-guide/permissions.html for more information
```python
# permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS

class AdminOrReadOnly(BasePermission):
    """
    Read permission for everyone. Only admins can modify content.
    """
    def has_permission(self, request, view, obj=None):
        if (request.method in SAFE_METHODS or
            request.user and request.user.is_staff):
            return True
        return False

```
```python
# views.py
from rest_framework_proxy.views import ProxyView
from permissions import AdminOrReadOnly

class ItemListProxy(ProxyView):
    permission_classes = (AdminOrReadOnly,)
```


#License#

Copyright (c) 2014, Tomi Pajunen
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
