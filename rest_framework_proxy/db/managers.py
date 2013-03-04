from django.db.models.manager import Manager

from rest_framework_proxy.db.query import ProxyQuerySet


class ProxyManager(Manager):
    """
    Access remote resources
    """
    use_for_related_fields = True

    def get_query_set(self):
        return ProxyQuerySet(self.model)

    def page(self, page, size=None):
        return self.get_query_set().page(page, size)
