Django Rest Framework Proxy
====================

Provides views to redirect incoming request to another API server.

**Features:**

* Masquerade paths
* HTTP Basic Auth (between your API and backend API)
* Supported methods: GET/POST/PUT/PATCH
* File uploads

**TODO:**
* Pass auth information from original client to backend API

#Installation#

```bash
$ pip install django-rest-framework-proxy 
```
*Note: Not in PyPI yet*

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
            <td><code>{'user': None, 'password': None}</code></td>
            <td>Proxy requests using HTTP Basic Authentication.</td>
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
