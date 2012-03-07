# Copyright 2012 VPAC
#
# This file is part of django-placard.
#
# django-placard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# django-placard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with django-placard  If not, see <http://www.gnu.org/licenses/>.

from placard.tldap import backend

DEFAULT_LDAP_ALIAS = "default"

class ConnectionHandler(object):
    def __init__(self, databases):
        self.databases = databases
        self._connections = {}

    def __getitem__(self, alias):
        if alias in self._connections:
            return self._connections[alias]

        db = self.databases[alias]

        conn = backend.LDAPObject(db)
        self._connections[alias] = conn
        return conn

    def __iter__(self):
        return iter(self.databases)

    def all(self):
        return [self[alias] for alias in self]


