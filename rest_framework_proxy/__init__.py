__version__ = '1.0.0'

from django.db.models import signals

from rest_framework_proxy.db.managers import ProxyManager


def ensure_proxy_manager(sender, **kwargs):
    cls = sender

    if (hasattr(cls, 'get_resource_url') \
       and not isinstance(cls, ProxyManager)):
        sender.add_to_class('objects', ProxyManager())
        sender.add_to_class('_default_manager', ProxyManager())


signals.class_prepared.connect(ensure_proxy_manager)
