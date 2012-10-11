# Copyright 2012 VPAC
#
# This file is part of python-tldap.
#
# python-tldap is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# python-tldap is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with python-tldap  If not, see <http://www.gnu.org/licenses/>.

import tldap
import tldap.query
import django.utils.importlib

class LDAPmanager(object):
    def __init__(self):
        self._cls = None
        self._alias = None

    def contribute_to_class(self, cls, name):
        self._cls = cls
        setattr(cls, name, ManagerDescriptor(self))

    def db_manager(self, using):
        obj = copy.copy(self)
        obj._alias = using
        return obj

    #######################
    # PROXIES TO QUERYSET #
    #######################

    def get_query_set(self):
        return tldap.query.QuerySet(self._cls, self._alias)

    def all(self):
        return self.get_query_set()

    def get(self, *args, **kwargs):
        return self.get_query_set().get(*args, **kwargs)

    def get_or_create(self, **kwargs):
        return self.get_query_set().get_or_create(**kwargs)

    def create(self, **kwargs):
        return self.get_query_set().create(**kwargs)

    def filter(self, *args, **kwargs):
        return self.get_query_set().filter(*args, **kwargs)


    def using(self, *args, **kwargs):
        return self.get_query_set().using(*args, **kwargs)


    def base_dn(self, *args, **kwargs):
        return self.get_query_set().base_dn(*args, **kwargs)


class ManagerDescriptor(object):
    # This class ensures managers aren't accessible via model instances.
    # For example, Poll.objects works, but poll_obj.objects raises AttributeError.
    def __init__(self, manager):
        self._manager = manager

    def __get__(self, instance, cls=None):
        if instance is not None:
            raise AttributeError("Manager isn't accessible via %s instances" % cls.__name__)
        return self._manager

def _lookup(cls, in_cls):
    if isinstance(cls, str):
        module_name, _, name = cls.rpartition(".")
        module = django.utils.importlib.import_module(module_name)
        try:
            cls = getattr(module, name)
        except AttributeError:
            raise AttributeError("%s reference cannot be found in %s class" % (cls, in_cls.__name__))
    return(cls)

def _create_link_manager(superclass, linked_update):
    class LinkManager(superclass):
        def __init__(self, this_instance, this_key, linked_cls, linked_key):
            super(LinkManager,self).__init__()

            self._this_instance = this_instance
            self._this_key = this_key
            self._this_value = getattr(this_instance, this_key)
            self._linked_cls = linked_cls
            self._linked_key = linked_key

            self._cls = linked_cls

        def get_query_set(self):
            this_value = self._this_value
            if not isinstance(this_value, list):
                this_value = [ this_value ]

            query = None
            for v in this_value:
                kwargs = { self._linked_key: v }
                if query is None:
                    query = tldap.Q(**kwargs)
                else:
                    query = query | tldap.Q(**kwargs)
            return super(LinkManager,self).get_query_set().filter(query)

        if linked_update:

            def get_or_create(self, **kwargs):
                this_value = self._this_value
                linked_key = self._linked_key
                assert not isinstance(this_value, list)

                kwargs[linked_key] = this_value
                if linked_key in kwargs['defaults']:
                    kwargs['defaults'][linked_key].append(value)
                return super(LinkManager,self).get_or_create(**kwargs)

            def create(self, **kwargs):
                this_value = self._this_value
                linked_key = self._linked_key
                assert not isinstance(this_value, list)

                kwargs[linked_key] = this_value
                return super(LinkManager,self).create(**kwargs)

            def add(self, obj):
                linked_cls = self._linked_cls
                assert isinstance(obj, linked_cls)
                this_value = self._this_value
                assert not isinstance(this_value, list)

                linked_key = self._linked_key
                linked_value = getattr(obj, linked_key, [])
                if not isinstance(linked_value, list):
                    linked_value = [ linked_value ]

                if self._this_value not in linked_value:
                    linked_value.append(this_value)

                obj.save()

            def delete(self, obj):
                linked_cls = self._linked_cls
                assert isinstance(obj, linked_cls)
                this_value = self._this_value
                assert not isinstance(this_value, list)

                linked_key = self._linked_key
                linked_value = getattr(obj, linked_key, [])
                if not isinstance(linked_value, list):
                    linked_value = [ linked_value ]

                if self._this_value in linked_value:
                    linked_value.remove(this_value)

                obj.save()

        else:

            def get_or_create(self, **kwargs):
                this_instance = self._this_instance
                this_key = self._this_key
                this_value = self._this_value
                linked_key = self._linked_key

                if not isinstance(this_value, list):
                    this_value = [ this_value ]
                    setattr(this_instance, this_key, this_value)

                r = super(LinkManager,self).get_or_create(**kwargs)
                v = kwargs[linked_key]
                if v not in this_value:
                    this_value.append(v)

                # yuck. but what else can we do?
                this_instance.save()
                return r

            def create(self, **kwargs):
                this_instance = self._this_instance
                this_key = self._this_key
                this_value = self._this_value
                linked_key = self._linked_key

                if not isinstance(this_value, list):
                    this_value = [ this_value ]
                    setattr(this_instance, this_key, this_value)

                r = super(LinkManager,self).create(**kwargs)
                v = kwargs[linked_key]
                if v not in this_value:
                    this_value.append(v)

                # yuck. but what else can we do?
                this_instance.save()
                return r

            def add(self, obj):
                self._this_value += obj.linked_key
                self._this_instance.save()

            def delete(self, obj):
                self._this_value -= obj.linked_key
                self._this_instance.save()

            def add(self, obj):
                linked_cls = self._linked_cls
                assert isinstance(obj, linked_cls)

                this_instance = self._this_instance
                this_value = self._this_value
                if not isinstance(this_value, list):
                    this_value = [ this_value ]

                linked_key = self._linked_key
                linked_value = getattr(obj, linked_key, [])
                assert not isinstance(linked_value, list)

                if linked_value not in self._this_value:
                    this_value.append(linked_value)

                this_instance.save()

            def delete(self, obj):
                linked_cls = self._linked_cls
                assert isinstance(obj, linked_cls)

                this_instance = self._this_instance
                this_value = self._this_value
                if not isinstance(this_value, list):
                    this_value = [ this_value ]

                linked_key = self._linked_key
                linked_value = getattr(obj, linked_key, [])
                assert not isinstance(linked_value, list)

                if linked_value in self._this_value:
                    this_value.remove(linked_value)

                this_instance.save()

    return LinkManager

class ManyToManyDescriptor(object):
    def __init__(self, this_key, linked_cls, linked_key, linked_update, related_name=None):
        self._this_key = this_key
        self._linked_cls = linked_cls
        self._linked_key = linked_key
        self._linked_update = linked_update
        self._related_name = related_name

    def contribute_to_class(self, cls, name):
        setattr(cls, name, self)
        if self._related_name is not None:
            reverse = ManyToManyDescriptor(self._linked_key, cls, self._this_key, not self._linked_update)
            setattr(self._linked_cls, self._related_name, reverse)

    def __get__(self, instance, cls=None):
        if instance is None:
            raise AttributeError("Manager isn't accessible via %s class" % cls.__name__)

        linked_cls = _lookup(self._linked_cls, cls)
        superclass = linked_cls.objects.__class__
        LinkManager = _create_link_manager(superclass, self._linked_update)
        return LinkManager(instance, self._this_key, linked_cls, self._linked_key)

class ManyToOneDescriptor(object):
    def __init__(self, this_key, linked_cls, linked_key, related_name=None):
        self._this_key = this_key
        self._linked_cls = linked_cls
        self._linked_key = linked_key
        self._related_name = related_name

    def contribute_to_class(self, cls, name):
        setattr(cls, name, self)
        if self._related_name is not None:
            reverse = OneToManyDescriptor(self._linked_key, cls, self._this_key)
            setattr(self._linked_cls, self._related_name, reverse)

    def __get__(self, instance, cls=None):
        if instance is None:
            raise AttributeError("Manager isn't accessible via %s class" % cls.__name__)

        linked_cls = _lookup(self._linked_cls, cls)
        superclass = linked_cls.objects.__class__
        LinkManager = _create_link_manager(superclass, False)
        lm = LinkManager(instance, self._this_key, linked_cls, self._linked_key)
        return lm.get()

    def __set__(self, instance, value):
        this_key = self._this_key
        linked_key = self._linked_key
        if value is not None:
            linked_value = getattr(value, linked_key)
        else:
            linked_value = None
        setattr(instance, this_key, linked_value)

class OneToManyDescriptor(object):
    def __init__(self, this_key, linked_cls, linked_key, related_name=None):
        self._this_key = this_key
        self._linked_cls = linked_cls
        self._linked_key = linked_key
        self._related_name = related_name

    def contribute_to_class(self, cls, name):
        setattr(cls, name, self)
        if self._related_name is not None:
            reverse = ManyToOneDescriptor(self._linked_key, cls, self._this_key)
            setattr(self._linked_cls, self._related_name, reverse)

    def __get__(self, instance, cls=None):
        if instance is None:
            raise AttributeError("Manager isn't accessible via %s class" % cls.__name__)

        linked_cls = _lookup(self._linked_cls, cls)
        superclass = linked_cls.objects.__class__
        LinkManager = _create_link_manager(superclass, True)
        return LinkManager(instance, self._this_key, linked_cls, self._linked_key)

