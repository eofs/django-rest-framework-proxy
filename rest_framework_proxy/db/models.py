import requests

from django.db import models, DatabaseError
from django.db.models import signals
from django.db.models.base import ModelBase
from django.db.models.fields import AutoField

from rest_framework_proxy.exceptions import RemoteModelException
from rest_framework_proxy.utils import resolve_resource


class ProxyModelBase(ModelBase):
    def __new__(cls, name, bases, attrs):
        """
        Copy of the first few lines from ModelBase's __new__ method. We need to filters
        parents against ProxyModelBase.
        """
        super_new = super(ModelBase, cls).__new__

        # six.with_metaclass() inserts an extra class called 'NewBase' in the
        # inheritance tree: Model -> NewBase -> object. But the initialization
        # should be executed only once for a given model class.

        # attrs will never be empty for classes declared in the standard way
        # (ie. with the `class` keyword). This is quite robust.
        if name == 'NewBase' and attrs == {}:
            return super_new(cls, name, bases, attrs)

        # Also ensure initialization is only performed for subclasses of Model
        # (excluding Model class itself).
        parents = [b for b in bases if isinstance(b, ProxyModelBase) and
                not (b.__name__ == 'NewBase' and b.__mro__ == (b, object))]
        if not parents:
            return super_new(cls, name, bases, attrs)

        # Jump back to original __new__ method
        return super(ProxyModelBase, cls).__new__(cls, name, bases, attrs)


class ProxyModel(models.Model):
    """
    A model that access remote resources.
    """
    __metaclass__ = ProxyModelBase


    def get_resource(self):
        resource_class = resolve_resource(self.get_resource_class())
        return resource_class()

    def save_base(self, raw=False, cls=None, origin=None, force_insert=False,
                  force_update=False, using=None, update_fields=None):
        """
        Does the heavy-lifting involved in saving. Subclasses shouldn't need to
        override this method. It's separate from save() in order to hide the
        need for overrides of save() to pass around internal-only parameters
        ('raw', 'cls', and 'origin').
        """

        assert not (force_insert and (force_update or update_fields))
        assert update_fields is None or len(update_fields) > 0
        if cls is None:
            cls = self.__class__
            meta = cls._meta
            if not meta.proxy:
                origin = cls
        else:
            meta = cls._meta

        if origin and not meta.auto_created:
            signals.pre_save.send(sender=origin, instance=self, raw=raw,
                                  update_fields=update_fields)

        # If we are in a raw save, save the object exactly as presented.
        # That means that we don't try to be smart about saving attributes
        # that might have come from the parent class - we just save the
        # attributes we have been given to the class we have been given.
        # We also go through this process to defer the save of proxy objects
        # to their actual underlying model.
        if not raw or meta.proxy:
            if meta.proxy:
                org = cls
            else:
                org = None
            for parent, field in meta.parents.items():
                # At this point, parent's primary key field may be unknown
                # (for example, from administration form which doesn't fill
                # this field). If so, fill it.
                if field and getattr(self, parent._meta.pk.attname) is None and getattr(self, field.attname) is not None:
                    setattr(self, parent._meta.pk.attname, getattr(self, field.attname))

                self.save_base(cls=parent, origin=org,
                               update_fields=update_fields)

                if field:
                    setattr(self, field.attname, self._get_pk_val(parent._meta))
                    # Since we didn't have an instance of the parent handy, we
                    # set attname directly, bypassing the descriptor.
                    # Invalidate the related object cache, in case it's been
                    # accidentally populated. A fresh instance will be
                    # re-built from the database if necessary.
                    cache_name = field.get_cache_name()
                    if hasattr(self, cache_name):
                        delattr(self, cache_name)

            if meta.proxy:
                return

        if not meta.proxy:
            non_pks = [f for f in meta.local_fields if not f.primary_key]

            if update_fields:
                non_pks = [f for f in non_pks if f.name in update_fields or f.attname in update_fields]

            # First, try an UPDATE. If that doesn't update anything, do an INSERT.
            pk_val = self._get_pk_val(meta)
            pk_set = pk_val is not None
            record_exists = True
            manager = cls._base_manager
            resource = self.get_resource()

            if pk_set:
                # Determine if we should do an update (pk already exists, forced update,
                # no force_insert)
                if (force_update or update_fields) or not force_insert:
                    if force_update or non_pks:
                        values = [(f.attname, (raw and getattr(self, f.attname) or f.pre_save(self, False))) for f in non_pks]
                        if values:
                            response = requests.patch(resource.get_url(pk_val), headers=resource.get_headers(),
                                           data=self._request_data(values),
                                           auth=resource.get_authentication())

                            status = response.status_code in (requests.status_codes.codes.ok,
                                                              requests.status_codes.codes.created)

                            if force_update and not status:
                                raise DatabaseError("Forced update did not affect any rows.")
                            if update_fields and not status:
                                raise DatabaseError("Save with update_fields did not affect any rows.")
                else:
                    record_exists = False
            if not pk_set or not record_exists:
                if meta.order_with_respect_to:
                    raise NotImplementedError('Model meta option order_with_respect_to is not implemented yet')

                fields = meta.local_fields
                if not pk_set:
                    if force_update or update_fields:
                        raise ValueError("Cannot force an update in save() with no primary key.")
                    fields = [(f.attname, getattr(self, f.attname)) for f in fields if not isinstance(f, AutoField)]

                record_exists = False

                update_pk = bool(meta.has_auto_field and not pk_set)
                import pdb; pdb.set_trace() ### XXX BREAKPOINT

                response = requests.post(resource.get_url(), headers=resource.get_headers(),
                                        data=self._request_data(fields),
                                        auth=resource.get_authentication())

                status = response.status_code in (requests.status_codes.codes.ok,
                                                  requests.status_codes.codes.created)

                if not status:
                    raise DatabaseError('Could not create a new object. Server reported HTTP code %d' % response.status_code)

                data = resource.parse(response)
                print data

                result = manager._insert([self], fields=fields, return_id=update_pk, using=using, raw=raw)

                if update_pk:
                    setattr(self, meta.pk.attname, result)
            #transaction.commit_unless_managed(using=using)

        # Store the database on which the object was saved
        self._state.db = using
        # Once saved, this is no longer a to-be-added instance.
        self._state.adding = False

        # Signal that the save is complete
        if origin and not meta.auto_created:
            signals.post_save.send(sender=origin, instance=self, created=(not record_exists),
                                   update_fields=update_fields, raw=raw)

    def _request_data(self, values):
        resource = self.get_resource()

        fields = [v[0] for v in values]
        data = dict((k, v) for k, v in values)

        serializer = resource.get_serializer(instance=self, data=data)
        # Override which fields should be used
        serializer.opts.fields = fields

        if serializer.is_valid():
            return serializer.data
        raise RemoteModelException('Serializer did not validate')
