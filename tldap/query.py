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

# Used to control how many objects are worked with at once in some cases (e.g.
# when deleting objects).
ITER_CHUNK_SIZE = 100

# The maximum number of items to display in a QuerySet.__repr__
REPR_OUTPUT_SIZE = 20

import ldap
import ldap.filter

import tldap

import copy

import django.utils.tree

class QuerySet(object):
    """
    Represents a lazy database lookup for a set of objects.
    """
    def __init__(self, cls, alias):
        assert cls is not None

        self._cls = cls
        self._dn = None
        self._alias = alias
        self._query = None
        self._base_dn = None
        self._iter = None
        self._result_cache = None

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
        # Since __len__ is called quite frequently (for example, as part of
        # list(qs), we make some effort here to be as efficient as possible
        # whilst not messing up any existing iterators against the QuerySet.
        if self._result_cache is None:
            if self._iter:
                self._result_cache = list(self._iter)
            else:
                self._result_cache = list(self.iterator())
        elif self._iter:
            self._result_cache.extend(self._iter)
        return len(self._result_cache)

    def __iter__(self):
        if self._result_cache is None:
            self._iter = self.iterator()
            self._result_cache = []
        if self._iter:
            return self._result_iter()
        # Python's list iterator is better than our version when we're just
        # iterating over the cache.
        return iter(self._result_cache)

    def _result_iter(self):
        pos = 0
        while 1:
            upper = len(self._result_cache)
            while pos < upper:
                yield self._result_cache[pos]
                pos = pos + 1
            if not self._iter:
                raise StopIteration
            if len(self._result_cache) <= pos:
                self._fill_cache()


    def __getitem__(self, k):
        """
        Retrieves an item or slice from the set of results.
        """
        return list(self)[k]

    def __and__(self, other):
        assert isinstance(other, QuerySet)
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

    def _get_filter_item(self, name, value):
        name, _, operation = name.rpartition("__")
        if name == "":
            name, operation = operation, None

        if operation is None:
            return ldap.filter.filter_format("(%s=%s)",[name, value])
        elif operation == "contains":
            assert value != ""
            return ldap.filter.filter_format("(%s=*%s*)",[name, value])
        else:
            raise ValueError("Unknown search operation %s"%operation)

    def _get_filter(self, q):
        if q.negated:
            op = "!"
        elif q.connector == tldap.Q.AND:
            op = "&"
        elif q.connector == tldap.Q.OR:
            op = "|"
        else:
            raise ValueError("Invalid value of op found")

        search = []
        for child in q.children:
            if isinstance(child, django.utils.tree.Node):
                search.append(self._get_filter(child))
            else:
                name,value = child
                try:
                    field = self._cls._meta.get_field_by_name(name)
                except KeyError:
                    field = tldap.fields.CharField()
                if isinstance(value, list) and len(value)==1:
                    value = value[0]
                    assert isinstance(value, str)
                if isinstance(value, list):
                    s = []
                    for v in value:
                        v = field.value_to_db(v)
                        s.append(self._get_filter_item(name, v))
                    search.append("(&".join(search) + ")")
                else:
                    value = field.value_to_db(value)
                    search.append(self._get_filter_item(name, value))

        return "("+ op + "".join(search) + ")"

    def _get_dn_filter(self, q):
        dn_list = []

        if q.connector == tldap.Q.OR:
            pass
        elif q.connector == tldap.Q.AND and len(q.children)==1:
            pass
        else:
            return None

        for child in q.children:
            if isinstance(child, django.utils.tree.Node):
                tmp_list = self._get_dn_filter(child)
                if tmp_list is None:
                    return None
                dn_list.extend(tmp_list)
                tmp_list = None
            else:
                name,value = child
                if name != "dn":
                    return None
                dn_list.append(value)

        return dn_list

    def iterator(self):
        """
        An iterator over the results from applying this QuerySet to the
        database.
        """

        # get object classes to search
        object_classes = self._cls._meta.search_classes or self._cls._meta.object_classes

        # add object classes to search array
        query = tldap.Q()
        for oc in object_classes:
            query = query & tldap.Q(objectClass=oc)

        # try and get a list of dn to search for
        dn_list = self._get_dn_filter(self._query)
        if dn_list is not None:
            # success, we only search for these dn
            scope = ldap.SCOPE_BASE
        else:
            # failed, we have to search for other attributes

            # add filter spec to search array
            if self._query is not None:
                query = query & self._query

            # do a SUBTREE search
            scope = ldap.SCOPE_SUBTREE

            # create a "list" of base_dn to search
            base_dn = self._base_dn or self._cls._meta.base_dn
            assert base_dn is not None
            dn_list = [ base_dn ]


        # set the database we should use as required
        alias = self._alias or tldap.DEFAULT_LDAP_ALIAS

        # get list of field names we support
        fields = self._cls._meta.fields
        field_names = self._cls._meta.get_all_field_names()

        # construct search filter string
        search_filter = self._get_filter(query)

        # repeat for every dn
        for base_dn in dn_list:
            assert base_dn is not None

            try:
                # get the results
                for i in tldap.connections[alias].search(base_dn, scope, search_filter, field_names):
                    # create new object
                    o = self._cls()

                    # set dn manually
                    setattr(o, '_dn', i[0])

                    # set the other fields
                    for field in fields:
                        name = field.name
                        value = i[1].get(name, [])
                        value = field.to_python(value)
                        setattr(o, name, value)

                    # save raw db values for latter use
                    o._db_values[alias] = i[1]

                    # save database alias for latter use
                    o._alias = alias

                    # give caller this result
                    yield o
            except ldap.NO_SUCH_OBJECT:
                # return with no results
                pass

    def get(self, *args, **kwargs):
        """
        Performs the query and returns a single object matching the given
        keyword arguments.
        """
        qs = self.filter(*args, **kwargs)
        num = len(qs)
        if num == 1:
            return qs._result_cache[0]
        if not num:
            raise self._cls.DoesNotExist("%s matching query does not exist."
                    % self._cls._meta.object_name)
        raise self._cls.MultipleObjectsReturned("get() returned more than one %s -- it returned %s! Lookup parameters were %s"
                % (self._cls._meta.object_name, num, kwargs))

    def create(self, **kwargs):
        """
        Creates a new object with the given kwargs, saving it to the database
        and returning the created object.
        """
        obj = self._cls(**kwargs)
        obj.save(force_add=True, using=self._alias)
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
            obj = self._cls(**params)
            obj.save(force_add=True, using=self._alias)
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

    def using(self, alias):
        """
        Selects which database this QuerySet should excecute it's query against.
        """
        clone = self._clone()
        clone._alias = alias
        return clone

    def base_dn(self, base_dn):
        qs = self._clone()
        qs._base_dn = base_dn
        return qs

    ###################################
    # PUBLIC INTROSPECTION ATTRIBUTES #
    ###################################

    ###################
    # PRIVATE METHODS #
    ###################

    def _clone(self):
        qs = QuerySet(self._cls, self._alias)
        qs._query = copy.deepcopy(self._query)
        qs._base_dn = self._base_dn
        return qs

    def _fill_cache(self, num=None):
        """
        Fills the result cache with 'num' more entries (or until the results
        iterator is exhausted).
        """
        if self._iter:
            try:
                for i in range(num or ITER_CHUNK_SIZE):
                    self._result_cache.append(self._iter.next())
            except StopIteration:
                self._iter = None

    def _merge_sanity_check(self, other):
        """
        Checks that we are merging two comparable QuerySet classes. By default
        this does nothing, but see the ValuesQuerySet for an example of where
        it's useful.
        """
        pass


class EmptyQuerySet(QuerySet):
    def __init__(self, cls, alias):
        super(EmptyQuerySet, self).__init__(cls, alias)
        self._result_cache = []

    def __and__(self, other):
        assert isinstance(other, QuerySet)
        return self._clone()

    def __or__(self, other):
        assert isinstance(other, QuerySet)
        return other._clone()

    def count(self):
        return 0

    def delete(self):
        pass

    def _clone(self, klass=None, setup=False, **kwargs):
        c = super(EmptyQuerySet, self)._clone(klass, setup=setup, **kwargs)
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

