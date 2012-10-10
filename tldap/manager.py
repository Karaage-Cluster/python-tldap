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

import tldap.query

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

    def __get__(self, instance, type=None):
        if instance != None:
            raise AttributeError("Manager isn't accessible via %s instances" % type.__name__)
        return self._manager
