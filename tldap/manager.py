# Copyright 2012-2014 Brian May
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

""" The default manager's and linkdescriptors used for tldap objects.

Terminology:

primary key
    is the key that is not changed.
f / foriegn
    is the object containing the primary key.
f_key
    is this key, i.e. the primary key in the foriegn object.
f_key
    is always a single value.

foriegn key
    is the referenced key.
p / primary
    is the object containing the foriegn key.
p_value
    is this key, i.e. the foriegn key in the primary object.

this
    is the object being operated on.
linked
    is the object being referenced for this operation.

if p_value_is_list is true then p_value must be a list.
if p_value_is_list is false then p_value must be a single value.
"""
from __future__ import absolute_import

import tldap
import tldap.query
import importlib
import copy


class Manager(object):
    """ The base manager class. """

    def __init__(self):
        self._cls = None
        self._alias = tldap.DEFAULT_LDAP_ALIAS
        self._settings = None
        self._base_dn = None
        # base_dn = None means lookup automatically at query time from class

    def contribute_to_class(self, cls, name):
        self._cls = cls
        setattr(cls, name, ManagerDescriptor(self))

    def db_manager(self, using=None, settings=None, base_dn=None):
        obj = copy.copy(self)
        if using is not None:
            obj._alias = using
        if settings is not None:
            obj._settings = settings
        if base_dn is not None:
            obj._base_dn = base_dn
        return obj

    #######################
    # PROXIES TO QUERYSET #
    #######################

    def get_empty_query_set(self):
        return tldap.query.EmptyQuerySet(
            self._cls, self._alias, self._settings, self._base_dn)

    def get_query_set(self):
        """Returns a new QuerySet object.  Subclasses can override this method
        to easily customize the behavior of the Manager.
        """
        return tldap.query.QuerySet(
            self._cls, self._alias, self._settings, self._base_dn)

    def none(self):
        return self.get_empty_query_set()

    def all(self):
        return self.get_query_set()

    def iterator(self):
        return self.get_query_set().iterator()

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
    # This class ensures managers aren't accessible via model instances.  For
    # example, Poll.objects works, but poll_obj.objects raises AttributeError.
    def __init__(self, manager):
        self._manager = manager

    def __get__(self, instance, cls=None):
        if instance is not None:
            raise AttributeError(
                "Manager isn't accessible via %s instances" % cls.__name__)
        return self._manager


def _lookup(cls):
    if isinstance(cls, str):
        module_name, _, name = cls.rpartition(".")
        module = importlib.import_module(module_name)
        try:
            cls = getattr(module, name)
        except AttributeError:
            raise AttributeError("%s reference cannot be found" % cls)
    return(cls)


def _create_link_manager(superclass, linked_is_p, p_value_is_list):
    class LinkManager(superclass):
        def __init__(self, this_instance, this_key, linked_cls, linked_key):
            super(LinkManager, self).__init__()

            self._this_instance = this_instance
            self._this_key = this_key
            self._linked_cls = linked_cls
            self._linked_key = linked_key

            # we want queries to use the same LDAP connection for this_instance
            self._alias = this_instance._alias
            self._settings = this_instance._settings
            # we want queries to be based on the linked_cls type
            self._cls = linked_cls
            self._base_dn = None

        def f_to_p(self, value):
            return value

        def p_to_f(self, value):
            return value

        def is_f_eq_p(self, p_value, f_value):
            assert not isinstance(p_value, list)
            return f_value == p_value

        def _get_query_set(self, this_value, linked_key):
            if this_value is None:
                this_value = []

            if not isinstance(this_value, list):
                this_value = [this_value]

            query = self.get_empty_query_set()
            for v in this_value:
                kwargs = {linked_key: v}
                query = query | (
                    super(LinkManager, self).get_query_set().filter(**kwargs))
            return query.using(
                self._this_instance._alias,
                self._this_instance._settings)

        def _add(self, p_instance, p_key, f_instance, f_key):
            p_value = getattr(p_instance, p_key)
            f_value = getattr(f_instance, f_key)
            assert not isinstance(f_value, list)
            assert f_value is not None
            f_value = self.f_to_p(f_value)

            if p_value_is_list:
                found = False
                for x in p_value:
                    if self.is_f_eq_p(f_value, x):
                        found = True
                if not found:
                    p_value.append(f_value)
            else:
                assert not isinstance(p_value, list)
                assert p_value is None or self.is_f_eq_p(f_value, p_value)
                p_value = f_value
                setattr(p_instance, p_key, p_value)

        def _remove(self, p_instance, p_key, f_instance, f_key):
            p_value = getattr(p_instance, p_key)
            f_value = getattr(f_instance, f_key)
            assert not isinstance(f_value, list)
            assert f_value is not None
            f_value = self.f_to_p(f_value)

            if p_value_is_list:
                new_list = []
                for x in p_value:
                    if not self.is_f_eq_p(f_value, x):
                        new_list.append(x)
                p_value = new_list
            else:
                assert not isinstance(p_value, list)
                assert p_value is None or self.is_f_eq_p(f_value, p_value)
                p_value = None
            setattr(p_instance, p_key, p_value)

        def get_query_set(self):
            this_instance = self._this_instance
            this_key = self._this_key
            this_value = getattr(this_instance, this_key)
            linked_key = self._linked_key
            if linked_is_p:
                this_value = self.f_to_p(this_value)
            else:
                this_value = self.p_to_f(this_value)
            return self._get_query_set(this_value, linked_key)

        def clear(self, commit=True):
            for obj in list(self.get_query_set()):
                self.remove(obj, commit)

        if linked_is_p:

            def get_or_create(self, commit=True, **kwargs):
                f_instance = self._this_instance
                f_key = self._this_key
                f_value = getattr(f_instance, f_key)
                assert not isinstance(f_value, list)
                assert f_value is not None
                f_value = self.f_to_p(f_value)

                p_key = self._linked_key

                if p_value_is_list:
                    kwargs[p_key] = [f_value]
                    if p_key in kwargs['defaults']:
                        assert isinstance(kwargs['defaults'][p_key], list)
                        kwargs['defaults'][p_key].append(f_value)
                else:
                    kwargs[p_key] = f_value
                    if p_key in kwargs['defaults']:
                        assert not isinstance(kwargs['defaults'][p_key], list)
                        assert kwargs['defaults'][p_key] == f_value
                return super(LinkManager, self).get_or_create(**kwargs)

            def create(self, commit=True, **kwargs):
                f_instance = self._this_instance
                f_key = self._this_key
                f_value = getattr(f_instance, f_key)
                assert not isinstance(f_value, list)
                assert f_value is not None
                f_value = self.f_to_p(f_value)

                p_key = self._linked_key

                if p_value_is_list:
                    kwargs[p_key] = [f_value]
                else:
                    kwargs[p_key] = f_value
                return super(LinkManager, self).create(**kwargs)

            def add(self, obj, commit=True):
                p_instance = obj
                p_key = self._linked_key
                f_instance = self._this_instance
                f_key = self._this_key
                assert isinstance(p_instance, self._linked_cls)
                self._add(p_instance, p_key, f_instance, f_key)
                obj.save()

            def remove(self, obj, commit=True):
                p_instance = obj
                p_key = self._linked_key
                f_instance = self._this_instance
                f_key = self._this_key
                assert isinstance(p_instance, self._linked_cls)
                self._remove(p_instance, p_key, f_instance, f_key)
                obj.save()

        else:

            def get_or_create(self, commit=True, **kwargs):
                p_instance = self._this_instance
                p_key = self._this_key
                p_value = getattr(p_instance, p_key)
                f_key = self._linked_key
                f_value = self.f_to_p(kwargs[f_key])
                assert not isinstance(f_value, list)
                assert f_value is not None

                r = super(LinkManager, self).get_or_create(**kwargs)

                if p_value_is_list:
                    assert isinstance(p_value, list)
                    if f_value not in p_value:
                        p_value.append(f_value)
                else:
                    assert not isinstance(p_value, list)
                    assert p_value is None or p_value == r[0]
                    p_value = f_value
                    setattr(p_instance, p_key, p_value)

                if commit:
                    p_instance.save()
                return r

            def create(self, commit=True, **kwargs):
                p_instance = self._this_instance
                p_key = self._this_key
                p_value = getattr(p_instance, p_key)
                f_key = self._linked_key
                f_value = self.f_to_p(kwargs[f_key])
                assert not isinstance(f_value, list)
                assert f_value is not None

                r = super(LinkManager, self).create(**kwargs)

                if p_value_is_list:
                    assert isinstance(p_value, list)
                    if f_value not in p_value:
                        p_value.append(f_value)
                else:
                    assert not isinstance(p_value, list)
                    assert p_value is None or p_value == f_value
                    p_value = None
                    setattr(p_instance, p_key, p_value)

                if commit:
                    p_instance.save()
                return r

            def add(self, obj, commit=True):
                p_instance = self._this_instance
                p_key = self._this_key
                f_instance = obj
                f_key = self._linked_key
                assert isinstance(f_instance, self._linked_cls)
                self._add(p_instance, p_key, f_instance, f_key)
                if commit:
                    p_instance.save()

            def remove(self, obj, commit=True):
                p_instance = self._this_instance
                p_key = self._this_key
                f_instance = obj
                f_key = self._linked_key
                assert isinstance(f_instance, self._linked_cls)
                self._remove(p_instance, p_key, f_instance, f_key)
                if commit:
                    p_instance.save()

            if not p_value_is_list:
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
                    Retrieve this value. Unlike get returns None if there is no
                    value, instead of raisng an exception.
                    """
                    this_instance = self._this_instance
                    this_key = self._this_key
                    this_value = getattr(this_instance, this_key)
                    if this_value is None:
                        return None

                    return self.get()

    return LinkManager


class LinkDescriptor(object):
    """ Base class for any field that links to another object. """

    def __init__(self, this_key, linked_cls, linked_key,
                 linked_is_p, p_value_is_list, related_name=None):
        self._this_key = this_key
        self._linked_cls = linked_cls
        self._linked_key = linked_key
        self._linked_is_p = linked_is_p
        self._p_value_is_list = p_value_is_list
        self._related_name = related_name

    def contribute_to_class(self, cls, name):
        setattr(cls, name, self)
        if self._related_name is not None:
            reverse = self.get_reverse(cls)
            if self._related_name in self._linked_cls.__dict__:
                raise AttributeError(
                    "%s class member %s produces reverse member"
                    "%s in class %s that conflicts" %
                    (cls.__name__, name, self._related_name,
                        self._linked_cls.__name__))
            setattr(self._linked_cls, self._related_name, reverse)

    def get_manager(self, instance):
        linked_cls = _lookup(self._linked_cls)
        superclass = linked_cls._default_manager.__class__
        LinkManager = _create_link_manager(
            superclass,
            linked_is_p=self._linked_is_p,
            p_value_is_list=self._p_value_is_list)
        return LinkManager(instance, self._this_key,
                           linked_cls, self._linked_key)

    def get_translated_linked_value(self, value):
        return value

    def get_q_for_linked_instance(self, obj, operation):
        if operation is not None:
            raise ValueError("Unknown search operation %s" % operation)

        this_key = self._this_key

        linked_cls = _lookup(self._linked_cls)
        linked_key = self._linked_key
        assert isinstance(obj, linked_cls)
        linked_value = self.get_translated_linked_value(
            getattr(obj, linked_key))
        if not isinstance(linked_value, list):
            linked_value = [linked_value]

        if len(linked_value) == 0:
            return None

        v = linked_value[0]
        kwargs = {this_key: v}
        q = tldap.Q(**kwargs)
        for v in linked_value[1:]:
            kwargs = {this_key: v}
            q = q | tldap.Q(**kwargs)
        return q

    def __get__(self, instance, cls=None):
        if instance is None:
            raise AttributeError(
                "Manager isn't accessible via %s class" % cls.__name__)
        return self.get_manager(instance)


class ManyToManyDescriptor(LinkDescriptor):
    """ Field for this object that has an attribute containing a list of
    references to linked objects. """

    def __init__(self, **kwargs):
        super(ManyToManyDescriptor, self).__init__(
            p_value_is_list=True, **kwargs)

    def get_reverse(self, cls):
        return ManyToManyDescriptor(
            this_key=self._linked_key, linked_cls=cls,
            linked_key=self._this_key, linked_is_p=not self._linked_is_p)

    def __set__(self, instance, value):
        assert isinstance(value, list)
        lm = self.get_manager(instance)
        if self._linked_key:
            lm.clear()
            for v in value:
                lm.add(v)
        else:
            lm.clear(commit=False)
            for v in value:
                lm.add(v, commit=False)


class ManyToOneDescriptor(LinkDescriptor):
    """ Linked object has an attribute that can contain only one member, that
    refers to this object. This field links to the linked object. """
    def __init__(self, **kwargs):
        super(ManyToOneDescriptor, self).__init__(
            linked_is_p=False, p_value_is_list=False, **kwargs)

    def get_reverse(self, cls):
        return OneToManyDescriptor(
            this_key=self._linked_key, linked_cls=cls,
            linked_key=self._this_key)

    def __set__(self, instance, value):
        assert not isinstance(value, list)
        lm = self.get_manager(instance)
        lm.clear(commit=False)
        if value is not None:
            lm.add(value, commit=False)


class OneToManyDescriptor(LinkDescriptor):
    """ This object has an attribute, represented by this field, that can
    contain only one member, that refers to linked object. """
    def __init__(self, **kwargs):
        super(OneToManyDescriptor, self).__init__(
            linked_is_p=True, p_value_is_list=False, **kwargs)

    def get_reverse(self, cls):
        return ManyToOneDescriptor(
            this_key=self._linked_key, linked_cls=cls,
            linked_key=self._this_key)

    def __set__(self, instance, value):
        assert isinstance(value, list)
        lm = self.get_manager(instance)
        lm.clear()
        for v in value:
            lm.add(value)


class AliasDescriptor(object):
    """ This field is an alias to another field. """
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


def _create_ad_group_link_manager(superclass, linked_is_p, p_value_is_list):
    assert p_value_is_list
    superclass = _create_link_manager(superclass, linked_is_p, p_value_is_list)

    class AdLinkManager(superclass):

        def is_f_eq_p(self, f_value, p_value):
            return f_value.lower() == p_value.lower()

        if linked_is_p:

            def add(self, obj, commit=True):
                this_instance = self._this_instance
                this_key = "primaryGroupID"
                this_value = getattr(this_instance, this_key)
                assert this_value is None or isinstance(this_value, int)

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
                assert linked_value is None or isinstance(linked_value, int)

                if _sid_to_rid(this_value) != linked_value:
                    super(AdLinkManager, self).add(obj, commit)

            def get_query_set(self):
                this_instance = self._this_instance
                this_key = "dn"
                this_value = getattr(this_instance, this_key)
                linked_key = "memberOf"
                return self._get_query_set(this_value, linked_key)

    return AdLinkManager


class AdGroupLinkDescriptor(ManyToManyDescriptor):
    """ This field represents a link from an AD account to an AD group. """
    def __init__(self, **kwargs):
        super(AdGroupLinkDescriptor, self).__init__(
            this_key="dn", linked_key="member", linked_is_p=True, **kwargs)

    def get_reverse(self, cls):
        return AdAccountLinkDescriptor(linked_cls=cls)

    def get_q_for_linked_instance(self, obj, operation):
        # We have to do the search using this_key of memberOf, not dn,
        # as this makes it more efficient. Also dn searches are restricted.
        if operation is not None:
            raise ValueError(
                "Unknown search operation %s" % operation)

        this_key = "memberOf"

        linked_cls = _lookup(self._linked_cls)
        linked_key = "dn"
        assert isinstance(obj, linked_cls)
        linked_value = getattr(obj, linked_key)
        if not isinstance(linked_value, list):
            linked_value = [linked_value]

        if len(linked_value) == 0:
            return None

        v = linked_value.pop()
        kwargs = {this_key: v}
        q = tldap.Q(**kwargs)
        for v in linked_value:
            kwargs = {this_key: v}
            q = q | tldap.Q(**kwargs)
        return q

    def get_manager(self, instance):
        linked_cls = _lookup(self._linked_cls)
        superclass = linked_cls._default_manager.__class__
        LinkManager = _create_ad_group_link_manager(
            superclass,
            linked_is_p=self._linked_is_p,
            p_value_is_list=self._p_value_is_list)
        return LinkManager(
            instance, self._this_key, linked_cls, self._linked_key)


class AdAccountLinkDescriptor(ManyToManyDescriptor):
    """ This field represents a link from an AD group to an AD account. """
    def __init__(self, **kwargs):
        super(AdAccountLinkDescriptor, self).__init__(
            this_key="member", linked_key="dn", linked_is_p=False, **kwargs)

    def get_reverse(self, cls):
        return AdGroupLinkDescriptor(linked_cls=cls)

    def get_manager(self, instance):
        linked_cls = _lookup(self._linked_cls)
        superclass = linked_cls._default_manager.__class__
        LinkManager = _create_ad_group_link_manager(
            superclass,
            linked_is_p=self._linked_is_p,
            p_value_is_list=self._p_value_is_list)
        return LinkManager(
            instance, self._this_key, linked_cls, self._linked_key)


def _create_ad_primary_group_link_manager(superclass,
                                          linked_is_p, p_value_is_list):
    superclass = _create_link_manager(superclass, linked_is_p, p_value_is_list)

    class AdLinkManager(superclass):

        def __init__(self, domain_sid, *args, **kwargs):
            self.domain_sid = domain_sid
            super(AdLinkManager, self).__init__(*args, **kwargs)

        def f_to_p(self, value):
            return _sid_to_rid(value)

        def p_to_f(self, value):
            return _rid_to_sid(self.domain_sid, value)

    return AdLinkManager


class AdPrimaryAccountLinkDescriptor(OneToManyDescriptor):
    """ This field represents a link from a user to a primary AD group. Update
    operations not guaranteed to work, due to AD rules."""

    def __init__(self, domain_sid, **kwargs):
        self.domain_sid = domain_sid
        super(AdPrimaryAccountLinkDescriptor, self).__init__(
            this_key="objectSid", linked_key="primaryGroupID", **kwargs)

    def get_reverse(self, cls):
        return AdPrimaryGroupLinkDescriptor(
            linked_cls=cls, domain_sid=self.domain_sid)

    def get_manager(self, instance):
        linked_cls = _lookup(self._linked_cls)
        superclass = linked_cls._default_manager.__class__
        LinkManager = _create_ad_primary_group_link_manager(
            superclass,
            linked_is_p=self._linked_is_p,
            p_value_is_list=self._p_value_is_list)
        return LinkManager(
            this_instance=instance, this_key=self._this_key,
            linked_cls=linked_cls, linked_key=self._linked_key,
            domain_sid=self.domain_sid)

    def get_translated_linked_value(self, value):
        this_value = super(AdPrimaryAccountLinkDescriptor, self) \
            .get_translated_linked_value(value)
        return _rid_to_sid(self.domain_sid, this_value)


class AdPrimaryGroupLinkDescriptor(ManyToOneDescriptor):
    """ This field represents a link from a primary AD group to a user. Update
    operations operations not guaranteed to work, due to AD rules."""

    def __init__(self, domain_sid, **kwargs):
        self.domain_sid = domain_sid
        super(AdPrimaryGroupLinkDescriptor, self).__init__(
            this_key="primaryGroupID", linked_key="objectSid", **kwargs)

    def get_reverse(self, cls):
        return AdPrimaryAccountLinkDescriptor(
            this_key=self._linked_key,
            linked_cls=cls, linked_key=self._this_key,
            domain_sid=self.domain_sid)

    def get_manager(self, instance):
        linked_cls = _lookup(self._linked_cls)
        superclass = linked_cls._default_manager.__class__
        LinkManager = _create_ad_primary_group_link_manager(
            superclass,
            linked_is_p=self._linked_is_p,
            p_value_is_list=self._p_value_is_list)
        return LinkManager(
            this_instance=instance, this_key=self._this_key,
            linked_cls=linked_cls, linked_key=self._linked_key,
            domain_sid=self.domain_sid)

    def get_translated_linked_value(self, value):
        this_value = super(AdPrimaryGroupLinkDescriptor, self) \
            .get_translated_linked_value(value)
        return _sid_to_rid(this_value)
