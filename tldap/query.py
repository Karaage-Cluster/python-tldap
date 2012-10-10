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
        self._cls = cls
        self._alias = alias
        self._query = []
        self._base_dn = None
        self._iter = None
        self._result_cache = None

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


    ####################################
    # METHODS THAT DO DATABASE QUERIES #
    ####################################

    def _get_filter(self, q):
        if q.negated:
            op = "!"
        elif q.connector == "AND":
            op = "&"
        elif q.connector == "OR":
            op = "|"
        else:
            raise ValueError("Invalid value of op found")

        search = []
        for child in q.children:
            if isinstance(child, django.utils.tree.Node):
                search.append(self._get_filter(child))
            else:
                search.append(ldap.filter.filter_format("(%s=%s)",[child[0], child[1]]))

        return "("+ op + "".join(search) + ")"

    def iterator(self):
        """
        An iterator over the results from applying this QuerySet to the
        database.
        """

        # get object classes to search
        object_classes = self._cls._meta.object_classes

        # add object classes to search array
        query = tldap.Q()
        for oc in object_classes:
            query = query & tldap.Q(objectClass=oc)

        # add filter spec to search array
        for q in self._query:
            query = query & q

        # get dn to search for, if given do a SCOPE_BASE search with this as a base;
        # otherwise do a SCOPE_SUBTREE with base_dn as base.
        dn = self._dn

        # set the base_dn as required
        base_dn = dn or self._base_dn or self._cls._meta.base_dn
        assert base_dn is not None

        # set the database we should use as required
        alias = self._alias or tldap.DEFAULT_LDAP_ALIAS

        # get list of field names we support
        fields = self._cls._meta.fields
        field_names = [ f.name for f in fields ]

        # construct search filter string
        search_filter = self._get_filter(query)

        # work out the search scope
        scope = ldap.SCOPE_SUBTREE
        if dn is not None:
            scope = ldap.SCOPE_BASE

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
                    value = field.clean(value)
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
        dn = kwargs.pop('dn', None)

        clone = self._clone()
        if negate:
            clone._query.append(~tldap.Q(*args, **kwargs))
            clone._dn = dn
        else:
            clone._query.append(tldap.Q(*args, **kwargs))
            clone._dn = dn
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


