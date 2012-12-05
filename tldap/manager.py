# Copyright 2012 VPAC
#
# This file is part of django-tldap.
#
# django-tldap is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# django-tldap is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with django-tldap  If not, see <http://www.gnu.org/licenses/>.

import tldap
import tldap.query
import django.utils.importlib

class Manager(object):
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

    def get_empty_query_set(self):
        return tldap.query.EmptyQuerySet(self._cls, self._alias)

    def get_query_set(self):
        """Returns a new QuerySet object.  Subclasses can override this method
        to easily customize the behavior of the Manager.
        """
        return tldap.query.QuerySet(self._cls, self._alias)

    def none(self):
        return self.get_empty_query_set()

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

    def convert(self, *args, **kwargs):
        return self.get_query_set().convert(*args, **kwargs)

class ManagerDescriptor(object):
    # This class ensures managers aren't accessible via model instances.
    # For example, Poll.objects works, but poll_obj.objects raises AttributeError.
    def __init__(self, manager):
        self._manager = manager

    def __get__(self, instance, cls=None):
        if instance is not None:
            raise AttributeError("Manager isn't accessible via %s instances" % cls.__name__)
        return self._manager

def _lookup(cls):
    if isinstance(cls, str):
        module_name, _, name = cls.rpartition(".")
        module = django.utils.importlib.import_module(module_name)
        try:
            cls = getattr(module, name)
        except AttributeError:
            raise AttributeError("%s reference cannot be found" % cls)
    return(cls)

def _create_link_manager(superclass, linked_has_foreign_key, foreign_key_is_list):
    class LinkManager(superclass):
        def __init__(self, this_instance, this_key, linked_cls, linked_key):
            super(LinkManager,self).__init__()

            self._this_instance = this_instance
            self._this_key = this_key
            self._linked_cls = linked_cls
            self._linked_key = linked_key

            self._cls = linked_cls

        def get_translated_this_value(self):
            this_instance = self._this_instance
            this_key = self._this_key
            return getattr(this_instance, this_key)

        def get_translated_linked_value(self, value):
            return value

        def get_query_set(self):
            this_instance = self._this_instance
            this_key = self._this_key
            this_value = self.get_translated_this_value()
            if this_value is None:
                this_value = [ ]

            if not isinstance(this_value, list):
                this_value = [ this_value ]

            linked_key = self._linked_key

            query = self.get_empty_query_set()
            for v in this_value:
                kwargs = { linked_key: v }
                query = query | super(LinkManager,self).get_query_set().filter(**kwargs)
            return query.using(this_instance._alias)

        if linked_has_foreign_key:

            def get_or_create(self, **kwargs):
                this_instance = self._this_instance
                this_key = self._this_key
                this_value = self.get_translated_this_value()
                assert not isinstance(this_value, list)

                linked_key = self._linked_key

                if foreign_key_is_list:
                    kwargs[linked_key] = [ this_value ]
                    if linked_key in kwargs['defaults']:
                        assert isinstance(kwargs['defaults'][linked_key], list)
                        kwargs['defaults'][linked_key].append(this_value)
                else:
                    kwargs[linked_key] = this_value
                    if linked_key in kwargs['defaults']:
                        assert not isinstance(kwargs['defaults'][linked_key], list)
                        assert kwargs['defaults'][linked_key] == this_value
                return super(LinkManager,self).get_or_create(**kwargs)

            def create(self, **kwargs):
                this_instance = self._this_instance
                this_key = self._this_key
                this_value = self.get_translated_this_value()
                assert not isinstance(this_value, list)

                linked_key = self._linked_key

                if foreign_key_is_list:
                    kwargs[linked_key] = [ this_value ]
                else:
                    kwargs[linked_key] = this_value
                return super(LinkManager,self).create(**kwargs)

            def add(self, obj, commit=True):
                this_instance = self._this_instance
                this_key = self._this_key
                this_value = self.get_translated_this_value()
                assert not isinstance(this_value, list)

                linked_cls = self._linked_cls
                linked_key = self._linked_key
                assert isinstance(obj, linked_cls)
                linked_value = getattr(obj, linked_key)

                if foreign_key_is_list:
                    assert isinstance(linked_value, list)
                    if this_value not in linked_value:
                        linked_value.append(this_value)
                else:
                    assert not isinstance(linked_value, list)
                    linked_value = this_value
                    setattr(obj, linked_key, linked_value)

                obj.save()

            def remove(self, obj, commit=True):
                this_instance = self._this_instance
                this_key = self._this_key
                this_value = self.get_translated_this_value()
                assert not isinstance(this_value, list)

                linked_cls = self._linked_cls
                linked_key = self._linked_key
                assert isinstance(obj, linked_cls)
                linked_value = getattr(obj, linked_key)

                if foreign_key_is_list:
                    assert isinstance(linked_value, list)
                    if this_value in linked_value:
                        linked_value.remove(this_value)
                else:
                    assert not isinstance(linked_value, list)
                    assert linked_value is None or linked_value == this_value
                    linked_value = None
                    setattr(obj, linked_key, linked_value)

                obj.save()

            def clear(self, commit=True):
                for obj in self.get_query_set():
                    self.remove(obj)

        else:

            def get_or_create(self, commit=True, **kwargs):
                this_instance = self._this_instance
                this_key = self._this_key
                this_value = getattr(this_instance, this_key)
                linked_key = self._linked_key
                linked_value = self.get_translated_linked_value(kwargs[linked_key])
                assert not isinstance(linked_value, list)

                r = super(LinkManager,self).get_or_create(**kwargs)

                if foreign_key_is_list:
                    assert isinstance(this_value, list)
                    if linked_value not in this_value:
                        this_value.append(linked_value)
                else:
                    assert not isinstance(this_value, list)
                    assert this_value is None or this_value == r[0]
                    this_value = linked_value
                    self._this_value = this_value
                    setattr(this_instance, this_key, this_value)

                if commit:
                    this_instance.save()
                return r

            def create(self, commit=True, **kwargs):
                this_instance = self._this_instance
                this_key = self._this_key
                this_value = getattr(this_instance, this_key)
                linked_key = self._linked_key
                linked_value = self.get_translated_linked_value(kwargs[linked_key])
                assert not isinstance(linked_value, list)

                r = super(LinkManager,self).create(**kwargs)
                v = kwargs[linked_key]

                if foreign_key_is_list:
                    assert isinstance(this_value, list)
                    if linked_value not in this_value:
                        this_value.append(linked_value)
                else:
                    assert not isinstance(this_value, list)
                    assert this_value is None or this_value == linked_value
                    this_value = None
                    setattr(this_instance, this_key, this_value)

                if commit:
                    this_instance.save()
                return r

            def add(self, obj, commit=True):
                this_instance = self._this_instance
                this_key = self._this_key
                this_value = getattr(this_instance, this_key)

                linked_cls = self._linked_cls
                linked_key = self._linked_key
                assert isinstance(obj, linked_cls)
                linked_value = self.get_translated_linked_value(getattr(obj, linked_key))
                assert not isinstance(linked_value, list)

                if foreign_key_is_list:
                    assert isinstance(this_value, list)
                    if linked_value not in this_value:
                        this_value.append(linked_value)
                else:
                    assert not isinstance(this_value, list)
                    assert this_value is None or this_value == linked_value
                    this_value = linked_value
                    self._this_value = this_value
                    setattr(this_instance, this_key, this_value)

                if commit:
                    this_instance.save()

            def remove(self, obj, commit=True):
                this_instance = self._this_instance
                this_key = self._this_key
                this_value = getattr(this_instance, this_key)

                linked_cls = self._linked_cls
                linked_key = self._linked_key
                assert isinstance(obj, linked_cls)
                linked_value = self.get_translated_linked_value(getattr(obj, linked_key))
                assert not isinstance(linked_value, list)

                if foreign_key_is_list:
                    assert isinstance(this_value, list)
                    if linked_value in this_value:
                        this_value.remove(linked_value)
                else:
                    assert not isinstance(this_value, list)
                    assert this_value is None or this_value == linked_value
                    this_value = None
                    setattr(this_instance, this_key, this_value)

                if commit:
                    this_instance.save()

            def clear(self, commit=True):
                this_instance = self._this_instance
                this_key = self._this_key
                this_value = getattr(this_instance, this_key)

                # delete existing value
                if foreign_key_is_list:
                    this_value = []
                else:
                    this_value = None
                self._this_value = this_value
                setattr(this_instance, this_key, this_value)

                if commit:
                    this_instance.save()

            if not foreign_key_is_list:
                def is_set(self):
                    """
                    Does this manager point to a value, or is it None?
                    """
                    this_instance = self._this_instance
                    this_key = self._this_key
                    this_value = getattr(this_instance, this_key)
                    return this_value is not None

                def get_obj(self):
                    """
                    Retrieve this value. Unlike get returns None if there is no value,
                    instead of raisng an exception.
                    """
                    this_instance = self._this_instance
                    this_key = self._this_key
                    this_value = getattr(this_instance, this_key)
                    if this_value is None:
                        return None

                    return self.get()

    return LinkManager

class LinkDescriptor(object):
    def __init__(self, this_key, linked_cls, linked_key, linked_has_foreign_key, foreign_key_is_list, related_name=None):
        self._this_key = this_key
        self._linked_cls = linked_cls
        self._linked_key = linked_key
        self._linked_has_foreign_key = linked_has_foreign_key
        self._foreign_key_is_list = foreign_key_is_list
        self._related_name = related_name

    def contribute_to_class(self, cls, name):
        setattr(cls, name, self)
        if self._related_name is not None:
            reverse = self.get_reverse(cls)
            if self._related_name in self._linked_cls.__dict__:
                raise AttributeError("%s class member %s produces reverse member %s in class %s that conflicts" %
                    (cls.__name__, name, self._related_name, self._linked_cls.__name__))
            setattr(self._linked_cls, self._related_name, reverse)

    def get_manager(self, instance):
        linked_cls = _lookup(self._linked_cls)
        superclass = linked_cls._default_manager.__class__
        LinkManager = _create_link_manager(superclass,
                linked_has_foreign_key=self._linked_has_foreign_key,
                foreign_key_is_list=self._foreign_key_is_list)
        return LinkManager(instance, self._this_key, linked_cls, self._linked_key)

    def get_translated_linked_value(self, value):
        return value

    def get_q_for_linked_instance(self, obj, operation):
        if operation is not None:
            raise ValueError("Unknown search operation %s"%operation)

        this_key = self._this_key

        linked_cls = _lookup(self._linked_cls)
        linked_key = self._linked_key
        assert isinstance(obj, linked_cls)
        linked_value = self.get_translated_linked_value(getattr(obj, linked_key))
        if not isinstance(linked_value, list):
            linked_value = [ linked_value ]

        if len(linked_value) == 0:
            return None

        v = linked_value.pop()
        kwargs = { this_key: v }
        q = tldap.Q(**kwargs)
        for v in linked_value:
            kwargs = { this_key: v }
            q = q | tldap.Q(**kwargs)
        return q

    def __get__(self, instance, cls=None):
        if instance is None:
            raise AttributeError("Manager isn't accessible via %s class" % cls.__name__)
        return self.get_manager(instance)


class ManyToManyDescriptor(LinkDescriptor):
    def __init__(self, **kwargs):
        super(ManyToManyDescriptor, self).__init__(foreign_key_is_list=True, **kwargs)

    def get_reverse(self, cls):
        return ManyToManyDescriptor(this_key=self._linked_key, linked_cls=cls, linked_key=self._this_key, linked_has_foreign_key=not self._linked_has_foreign_key)

    def __set__(self, instance, value):
        assert isinstance(value, list)
        lm = self.get_manager(instance)
        if self._linked_key:
            lm.clear()
            for v in value:
                lm.add(value)
        else:
            lm.clear(commit=False)
            for v in value:
                lm.add(value, commit=False)

class ManyToOneDescriptor(LinkDescriptor):
    def __init__(self, **kwargs):
        super(ManyToOneDescriptor, self).__init__(linked_has_foreign_key=False, foreign_key_is_list=False, **kwargs)

    def get_reverse(self, cls):
        return OneToManyDescriptor(this_key=self._linked_key, linked_cls=cls, linked_key=self._this_key)

    def __set__(self, instance, value):
        assert not isinstance(value, list)
        lm = self.get_manager(instance)
        lm.clear(commit=False)
        if value is not None:
            lm.add(value, commit=False)

class OneToManyDescriptor(LinkDescriptor):
    def __init__(self, **kwargs):
        super(OneToManyDescriptor, self).__init__(linked_has_foreign_key=True, foreign_key_is_list=False, **kwargs)

    def get_reverse(self, cls):
        return ManyToOneDescriptor(this_key=self._linked_key, linked_cls=cls, linked_key=self._this_key)

    def __set__(self, instance, value):
        assert isinstance(value, list)
        lm = self.get_manager(instance)
        lm.clear()
        for v in value:
            lm.add(value)


class AliasDescriptor(object):
    def __init__(self, linked_key):
        self._linked_key = linked_key

    def __get__(self, instance, cls=None):
        return getattr(instance, self._linked_key)

    def __set__(self, instance, value):
        setattr(instance, self._linked_key, value)


def _sid_to_rid(sid):
    if sid is None:
        return None
    _, _, rid = sid.rpartition("-")
    return int(rid)


def _rid_to_sid(domain_sid, rid):
    if rid is None:
        return None
    assert isinstance(rid, int)
    return "S-1-5-%s-%s" % (domain_sid, rid)


def _create_ad_group_link_manager(superclass, linked_has_foreign_key, foreign_key_is_list):
    assert foreign_key_is_list
    superclass = _create_link_manager(superclass, linked_has_foreign_key, foreign_key_is_list)

    class AdLinkManager(superclass):

        if linked_has_foreign_key:

            def add(self, obj, commit=True):
                this_instance = self._this_instance
                this_key = "primaryGroupID"
                this_value = getattr(this_instance, this_key)
                assert isinstance(this_value, int)

                linked_cls = self._linked_cls
                linked_key = "objectSid"
                assert isinstance(obj, linked_cls)
                linked_value = getattr(obj, linked_key)

                if this_value != _sid_to_rid(linked_value):
                    super(AdLinkManager, self).add(obj, commit)

        else:

            def add(self, obj, commit=True):
                this_instance = self._this_instance
                this_key = "objectSid"
                this_value = getattr(this_instance, this_key)

                linked_cls = self._linked_cls
                linked_key = "primaryGroupID"
                assert isinstance(obj, linked_cls)
                linked_value = getattr(obj, linked_key)
                assert isinstance(linked_value, int)

                if _sid_to_rid(this_value) != linked_value:
                    super(AdLinkManager, self).add(obj, commit)

            def get_query_set(self):
                this_instance = self._this_instance
                this_key = "dn"
                this_value = getattr(this_instance, this_key)
                if this_value is None:
                    this_value = [ ]

                if not isinstance(this_value, list):
                    this_value = [ this_value ]

                linked_key = "memberOf"

                query = self.get_empty_query_set()
                for v in this_value:
                    kwargs = { linked_key: v }
                    query = query | super(superclass, self).get_query_set().filter(**kwargs)
                return query.using(this_instance._alias)

    return AdLinkManager


class AdGroupLinkDescriptor(ManyToManyDescriptor):
    def __init__(self, **kwargs):
        super(AdGroupLinkDescriptor, self).__init__(this_key="dn", linked_key="member", linked_has_foreign_key=True, **kwargs)

    def get_reverse(self, cls):
        return AdUserLinkDescriptor(linked_cls=cls)

    def get_q_for_linked_instance(self, obj, operation):
        # We have to do the search using this_key of memberOf, not dn,
        # as this makes it more efficient. Also dn searches are restricted.
        if operation is not None:
            raise ValueError("Unknown search operation %s"%operation)

        this_key = "memberOf"

        linked_cls = _lookup(self._linked_cls)
        linked_key = "dn"
        assert isinstance(obj, linked_cls)
        linked_value = getattr(obj, linked_key)
        if not isinstance(linked_value, list):
            linked_value = [ linked_value ]

        if len(linked_value) == 0:
            return None

        v = linked_value.pop()
        kwargs = { this_key: v }
        q = tldap.Q(**kwargs)
        for v in linked_value:
            kwargs = { this_key: v }
            q = q | tldap.Q(**kwargs)
        return q

    def get_manager(self, instance):
        linked_cls = _lookup(self._linked_cls)
        superclass = linked_cls._default_manager.__class__
        LinkManager = _create_ad_group_link_manager(superclass,
                linked_has_foreign_key=self._linked_has_foreign_key,
                foreign_key_is_list=self._foreign_key_is_list)
        return LinkManager(instance, self._this_key, linked_cls, self._linked_key)


class AdAccountLinkDescriptor(ManyToManyDescriptor):
    def __init__(self, **kwargs):
        super(AdAccountLinkDescriptor, self).__init__(this_key="member", linked_key="dn", linked_has_foreign_key=False, **kwargs)

    def get_reverse(self, cls):
        return AdGroupLinkDescriptor(linked_cls=cls)

    def get_manager(self, instance):
        linked_cls = _lookup(self._linked_cls)
        superclass = linked_cls._default_manager.__class__
        LinkManager = _create_ad_group_link_manager(superclass,
                linked_has_foreign_key=self._linked_has_foreign_key,
                foreign_key_is_list=self._foreign_key_is_list)
        return LinkManager(instance, self._this_key, linked_cls, self._linked_key)


def _create_ad_primary_group_link_manager(superclass, linked_has_foreign_key, foreign_key_is_list):
    superclass = _create_link_manager(superclass, linked_has_foreign_key, foreign_key_is_list)

    class AdLinkManager(superclass):

        def __init__(self, domain_sid, *args, **kwargs):
            self.domain_sid = domain_sid
            super(AdLinkManager, self).__init__(*args, **kwargs)

        if linked_has_foreign_key:

            def get_translated_this_value(self):
                this_value = super(AdLinkManager, self).get_translated_this_value()
                return _sid_to_rid(this_value)

            def get_translated_linked_value(self, value):
                this_value = super(AdLinkManager, self).get_translated_linked_value(value)
                return _rid_to_sid(self.domain_sid, this_value)

        else:

            def get_translated_this_value(self):
                this_value = super(AdLinkManager, self).get_translated_this_value()
                return _rid_to_sid(self.domain_sid, this_value)

            def get_translated_linked_value(self, value):
                this_value = super(AdLinkManager, self).get_translated_linked_value(value)
                return _sid_to_rid(this_value)

    return AdLinkManager


class AdPrimaryAccountLinkDescriptor(OneToManyDescriptor):

    def __init__(self, domain_sid, **kwargs):
        self.domain_sid = domain_sid
        super(AdPrimaryAccountLinkDescriptor, self).__init__(this_key="objectSid", linked_key="primaryGroupID", **kwargs)

    def get_reverse(self, cls):
        return AdPrimaryGroupLinkDescriptor(linked_cls=cls, domain_sid=self.domain_sid)

    def get_manager(self, instance):
        linked_cls = _lookup(self._linked_cls)
        superclass = linked_cls._default_manager.__class__
        LinkManager = _create_ad_primary_group_link_manager(superclass,
                linked_has_foreign_key=self._linked_has_foreign_key,
                foreign_key_is_list=self._foreign_key_is_list)
        return LinkManager(this_instance=instance, this_key=self._this_key, linked_cls=linked_cls, linked_key=self._linked_key, domain_sid=self.domain_sid)

    def get_translated_linked_value(self, value):
        this_value = super(AdPrimaryAccountLinkDescriptor, self).get_translated_linked_value(value)
        return _rid_to_sid(self.domain_sid, this_value)


class AdPrimaryGroupLinkDescriptor(ManyToOneDescriptor):

    def __init__(self, domain_sid, **kwargs):
        self.domain_sid = domain_sid
        super(AdPrimaryGroupLinkDescriptor, self).__init__(this_key="primaryGroupID", linked_key="objectSid", **kwargs)

    def get_reverse(self, cls):
        return AdPrimaryAccountLinkDescriptor(this_key=self._linked_key, linked_cls=cls, linked_key=self._this_key, domain_sid=self.domain_sid)

    def get_manager(self, instance):
        linked_cls = _lookup(self._linked_cls)
        superclass = linked_cls._default_manager.__class__
        LinkManager = _create_ad_primary_group_link_manager(superclass,
                linked_has_foreign_key=self._linked_has_foreign_key,
                foreign_key_is_list=self._foreign_key_is_list)
        return LinkManager(this_instance=instance, this_key=self._this_key, linked_cls=linked_cls, linked_key=self._linked_key, domain_sid=self.domain_sid)

    def get_translated_linked_value(self, value):
        this_value = super(AdPrimaryGroupLinkDescriptor, self).get_translated_linked_value(value)
        return _sid_to_rid(this_value)
