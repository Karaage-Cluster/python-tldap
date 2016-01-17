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

""" Used to perform LDAP queries. """

from __future__ import absolute_import

import six
import ldap3

import tldap
import tldap.manager
import tldap.helpers
import tldap.filter
from tldap.tree import Node


# Used to control how many objects are worked with at once in some cases (e.g.
# when deleting objects).
ITER_CHUNK_SIZE = 100

# The maximum number of items to display in a QuerySet.__repr__
REPR_OUTPUT_SIZE = 20


class QuerySet(object):
    """
    Represents a lazy database lookup for a set of objects.
    """
    def __init__(self, cls, using, settings, base_dn):
        assert cls is not None

        self._from_cls = None
        self._cls = cls
        self._dn = None
        self._alias = using
        self._settings = settings
        self._query = None
        self._base_dn = base_dn
        self._iter = None
        self._result_cache = None
        self._limits = None

    @property
    def model(self):
        return self._cls

    ########################
    # PYTHON MAGIC METHODS #
    ########################

    def __repr__(self):
        data = list(self[:REPR_OUTPUT_SIZE + 1])
        if len(data) > REPR_OUTPUT_SIZE:
            data[-1] = "...(remaining elements truncated)..."
        return repr(data)

    def __len__(self):
        self._fetch_all()
        return len(self._result_cache)

    def __iter__(self):
        self._fetch_all()
        return iter(self._result_cache)

    def __bool__(self):
        self._fetch_all()
        return bool(self._result_cache)

    def __nonzero__(self):      # Python 2 compatibility
        return type(self).__bool__(self)

    def __getitem__(self, k):
        """
        Retrieves an item or slice from the set of results.
        """
        if not isinstance(k, (slice,) + six.integer_types):
            raise TypeError
        if not isinstance(k, slice) and (k < 0):
            raise IndexError("Negative indexing is not supported.")
        if isinstance(k, slice) and (k.start is not None and k.start < 0):
            raise IndexError("Negative indexing is not supported.")
        if isinstance(k, slice) and (k.stop is not None and k.stop < 0):
            raise IndexError("Negative indexing is not supported.")

        if self._result_cache is not None:
            return self._result_cache[k]

        if isinstance(k, slice):
            qs = self._clone()
            if k.start is not None:
                start = int(k.start)
            else:
                start = 0
            if k.stop is not None:
                stop = int(k.stop)
            else:
                stop = None
            qs._limits = start, stop
            return k.step and list(qs)[::k.step] or qs
        qs = self._clone()
        qs._limits = k, k + 1
        return list(qs)[0]

    def __and__(self, other):
        assert isinstance(other, QuerySet)
        assert self._alias == other._alias
        assert self._settings == other._settings
        self._merge_sanity_check(other)
        if self._query is None:
            return other._clone()
        if isinstance(other, EmptyQuerySet):
            return other._clone()
        combined = self._clone()
        combined._query = combined._query & other._query
        return combined

    def __or__(self, other):
        assert isinstance(other, QuerySet)
        assert self._alias == other._alias
        assert self._settings == other._settings
        self._merge_sanity_check(other)
        combined = self._clone()
        if self._query is None:
            return combined
        if isinstance(other, EmptyQuerySet):
            return combined
        combined._query = combined._query | other._query
        return combined

    ####################################
    # METHODS THAT DO DATABASE QUERIES #
    ####################################

    def _get_filter_item(self, name, operation, value):
        """
        A field could be found for this term, try to get filter string for it.
        """
        assert isinstance(name, six.string_types)
        assert isinstance(value, six.string_types + (bytes,))
        if operation is None:
            return tldap.filter.filter_format(
                "(%s=%s)", [name, value])
        elif operation == "contains":
            assert value != ""
            return tldap.filter.filter_format(
                "(%s=*%s*)", [name, value])
        else:
            raise ValueError("Unknown search operation %s" % operation)

    def _get_filter(self, q):
        """
        Translate the Q tree into a filter string to search for, or None
        if no results possible.
        """
        # check the details are valid
        if q.negated and len(q.children) == 1:
            op = "!"
        elif q.connector == tldap.Q.AND:
            op = "&"
        elif q.connector == tldap.Q.OR:
            op = "|"
        else:
            raise ValueError("Invalid value of op found")

        # scan through every child
        search = []
        for child in q.children:
            # if this child is a node, then descend into it
            if isinstance(child, Node):
                search.append(self._get_filter(child))
            else:
                # otherwise get the values in this node
                name, value = child

                # split the name if possible
                name, _, operation = name.rpartition("__")
                if name == "":
                    name, operation = operation, None

                # replace pk with the real attribute
                if name == "pk":
                    name = self._cls._meta.pk

                # DN is a special case
                if name == "dn":
                    name = "entryDN:"
                    if isinstance(value, list):
                        s = []
                        for v in value:
                            s.append(self._get_filter_item(name, operation, v))
                        search.append("(&".join(search) + ")")

                    # or process just the single value
                    else:
                        search.append(
                            self._get_filter_item(name, operation, value))
                    continue

                # try to find field associated with name
                try:
                    field = self._cls._meta.get_field_by_name(name)
                except KeyError:
                    # no field found, try to lookup linked models
                    raise ValueError(
                        "Cannot do a search on %s "
                        "as we cannot find the field" % name)
                else:
                    # field was found
                    # try to turn list into single value
                    if isinstance(value, list) and len(value) == 1:
                        value = value[0]
                        assert isinstance(value, str)

                    # process as list
                    if isinstance(value, list):
                        s = []
                        for v in value:
                            v = field.value_to_db(v)
                            s.append(self._get_filter_item(name, operation, v))
                        search.append("(&".join(search) + ")")

                    # or process just the single value
                    else:
                        value = field.value_to_db(value)
                        search.append(
                            self._get_filter_item(name, operation, value))

        # output the results
        if len(search) == 1 and not q.negated:
            # just one non-negative term, return it
            return search[0]
        else:
            # multiple terms
            return "(" + op + "".join(search) + ")"

    def _clone_query(self, q):
        dst = tldap.Q()
        dst.connector = q.connector
        dst.negated = q.negated

        """
        Expands exandable q items, i.e. for relations between objects.
        """
        # scan through every child
        for child in q.children:

            # if this child is a node, then descend into it
            if isinstance(child, Node):
                dst.children.append(self._clone_query(child))
            else:
                dst.children.append(child)

        return dst

    def _expand_query(self, q):
        dst = tldap.Q()
        dst.connector = q.connector
        dst.negated = q.negated

        """
        Expands exandable q items, i.e. for relations between objects.
        """
        # scan through every child
        for child in q.children:

            # if this child is a node, then descend into it
            if isinstance(child, Node):
                dst.children.append(self._expand_query(child))
                continue

            # otherwise get the values in this node
            name, value = child

            # split the name if possible
            name, _, operation = name.rpartition("__")
            if name == "":
                name, operation = operation, None

            # replace pk with the real attribute
            if name == "pk":
                name = self._cls._meta.pk

            # dn searches are a special case
            if name == "dn":
                dst.children.append(child)
                continue

            # try to find field associated with name
            try:
                self._cls._meta.get_field_by_name(name)
                dst.children.append(child)
                continue
            except KeyError:
                # no field found, try to lookup linked models
                pass

            # get raw value from class
            cls_value = self._cls.__dict__.get(name, None)

            # fail for cases we don't understand
            if cls_value is None:
                raise ValueError(
                    "Cannot do a search on %s "
                    "as we do not know about it" % name)

            # fail for cases we don't understand
            if not isinstance(cls_value, tldap.manager.LinkDescriptor):
                raise ValueError(
                    "Cannot do a search on %s "
                    "as we do not know the type" % name)

            # ask the LinkDescriptor for a q tree
            child = cls_value.get_q_for_linked_instance(value, operation)

            # if child is None, then no results can be found
            # we need to handle this later.
            dst.children.append(child)

        # go through results
        new_children = []
        for term in dst.children:
            # if result is not None, keep it
            if term is not None:
                new_children.append(term)

            # a result of None means 0 results
            elif q.negated:
                # not 0 results is all results
                return tldap.Q(objectClass='*')
            elif q.connector == tldap.Q.AND:
                # 0 results and anything is still 0 results
                return None
            elif q.connector == tldap.Q.OR:
                # 0 results or anything is just anything
                pass
        dst.children = new_children

        # output the results
        if len(dst.children) == 0:
            # no search terms, all terms were None
            return None
        else:
            # multiple terms
            return dst

    def _get_search_params(self):
        # set the database we should use as required
        alias = self._alias or tldap.DEFAULT_LDAP_ALIAS
        connection = tldap.connections[alias]

        # get object classes to search
        if self._from_cls is None:
            object_classes = (
                self._cls._meta.search_classes or
                self._cls._meta.object_classes)
        else:
            object_classes = self._from_cls._meta.search_classes

        if self._query is not None:
            # expand query
            requested_query = self._expand_query(self._query)

        # add object classes to search array
        query = tldap.Q()
        for oc in object_classes:
            query = query & tldap.Q(objectClass=oc)

        # do a SUBTREE search
        scope = ldap3.SEARCH_SCOPE_WHOLE_SUBTREE

        # add requested query
        if self._query is not None:
            if requested_query is not None:
                query = query & requested_query
            else:
                query = None

        # create a "list" of base_dn to search
        base_dn = self.get_base_dn()
        assert base_dn is not None

        # get list of field names we support
        field_names = self._cls._meta.get_all_field_names()

        # construct search filter string
        if query is not None:
            search_filter = self._get_filter(query)
        else:
            search_filter = None

        return alias, connection, base_dn, scope, search_filter, field_names

    def iterator(self):
        """
        An iterator over the results from applying this QuerySet to the
        database.
        """
        # get search parameters
        alias, connection, base_dn, scope, search_filter, field_names = (
            self._get_search_params())
        if search_filter is None:
            return

        if self._limits is not None:
            start, stop = self._limits
            limit = stop
        else:
            start = 0
            limit = None

        # repeat for every dn
        fields = self._cls._meta.fields

        # get the results
        for i in connection.search(base_dn, scope,
                                   search_filter, field_names,
                                   limit=limit):
            if start > 0:
                start = start - 1
                continue

            # create new object
            o = self._cls(
                dn=i[0],
                using=alias,
                settings=self._settings,
            )

            # set the other fields
            for field in fields:
                name = field.name
                value = i[1].get(name, [])
                value = field.to_python(value)
                setattr(o, name, value)

            # save raw db values for latter use
            o._db_values = (
                tldap.helpers.CaseInsensitiveDict(i[1]))

            # give caller this result
            yield o

    def get(self, *args, **kwargs):
        """
        Performs the query and returns a single object matching the given
        keyword arguments.
        """
        clone = self.filter(*args, **kwargs)
        num = len(clone)
        if num == 1:
            return clone._result_cache[0]
        if not num:
            raise self._cls.DoesNotExist(
                "%s matching query does not exist." %
                self._cls._meta.object_name)
        raise self._cls.MultipleObjectsReturned(
            "get() returned more than one %s "
            "-- it returned %s! Lookup parameters were %s" %
            (self._cls._meta.object_name, num, kwargs))

    def create(self, **kwargs):
        """
        Creates a new object with the given kwargs, saving it to the database
        and returning the created object.
        """
        obj = self._cls(settings=self._settings, using=self._alias, **kwargs)
        obj.save(force_add=True)
        return obj

    def get_or_create(self, **kwargs):
        """
        Looks up an object with the given kwargs, creating one if necessary.
        Returns a tuple of (object, created), where created is a boolean
        specifying whether an object was created.
        """
        assert kwargs, \
            'get_or_create() must be passed at least one keyword argument'
        defaults = kwargs.pop('defaults', {})
        try:
            return self.get(**kwargs), False
        except self._cls.DoesNotExist:
            params = dict(kwargs)
            params.update(defaults)
            obj = self._cls(
                settings=self._settings, using=self._alias, **params)
            obj.save(force_add=True)
            return obj, True

    def none(self):
        """
        Returns an empty QuerySet.
        """
        return self._clone(klass=EmptyQuerySet)

    ##################################################################
    # PUBLIC METHODS THAT ALTER ATTRIBUTES AND RETURN A NEW QUERYSET #
    ##################################################################

    def filter(self, *args, **kwargs):
        """
        Returns a new QuerySet instance with the args ANDed to the existing
        set.
        """
        return self._filter_or_exclude(False, *args, **kwargs)

    def exclude(self, *args, **kwargs):
        """
        Returns a new QuerySet instance with NOT (args) ANDed to the existing
        set.
        """
        return self._filter_or_exclude(True, *args, **kwargs)

    def _filter_or_exclude(self, negate, *args, **kwargs):
        clone = self._clone()
        if negate:
            q = ~tldap.Q(*args, **kwargs)
        else:
            q = tldap.Q(*args, **kwargs)
        if clone._query is None:
            clone._query = q
        else:
            clone._query = clone._query & q
        return clone

    def using(self, using, settings=None):
        """
        Selects which database this QuerySet should excecute it's query
        against.
        """
        clone = self._clone()
        clone._alias = using
        clone._settings = settings
        return clone

    def base_dn(self, base_dn):
        qs = self._clone()
        qs._base_dn = base_dn
        return qs

    def get_base_dn(self):
        base_dn = self._base_dn
        if base_dn is None:
            base_dn = self._cls.get_default_base_dn(
                self._alias, self._settings)
        return base_dn

    def convert(self, cls):
        qs = self._clone()
        qs._from_cls = cls
        return qs

    ###################################
    # PUBLIC INTROSPECTION ATTRIBUTES #
    ###################################

    ###################
    # PRIVATE METHODS #
    ###################

    def _clone(self, klass=None):
        if klass is None:
            klass = self.__class__
        qs = klass(self._cls, self._alias, self._settings, self._base_dn)
        if self._query is not None:
            qs._query = self._clone_query(self._query)
        else:
            qs._query = None
        qs._base_dn = self._base_dn
        qs._from_cls = self._from_cls
        return qs

    def _fetch_all(self):
        if self._result_cache is None:
            self._result_cache = list(self.iterator())

    def _merge_sanity_check(self, other):
        """
        Checks that we are merging two comparable QuerySet classes. By default
        this does nothing, but see the ValuesQuerySet for an example of where
        it's useful.
        """
        pass


class EmptyQuerySet(QuerySet):
    """
    Represents an empty query set with no results.
    """
    def __init__(self, cls, alias, settings, base_dn):
        super(EmptyQuerySet, self).__init__(cls, alias, settings, base_dn)
        self._result_cache = []

    def __and__(self, other):
        assert isinstance(other, QuerySet)
        return self._clone()

    def __or__(self, other):
        assert isinstance(other, QuerySet)
        return other._clone()

    def delete(self):
        pass

    def _clone(self, klass=None, **kwargs):
        c = super(EmptyQuerySet, self)._clone(klass, **kwargs)
        c._result_cache = []
        return c

    def iterator(self):
        # This slightly odd construction is because we need an empty generator
        # (it raises StopIteration immediately).
        yield iter([]).next()

    def all(self):
        """
        Always returns EmptyQuerySet.
        """
        return self

    def filter(self, *args, **kwargs):
        """
        Always returns EmptyQuerySet.
        """
        return self

    def exclude(self, *args, **kwargs):
        """
        Always returns EmptyQuerySet.
        """
        return self
