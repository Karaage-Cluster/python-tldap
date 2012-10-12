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

class Options(object):
    def __init__(self, name, meta):
        self.meta = meta
        self._fields = {}
        self.object_classes = set(getattr(meta, 'object_classes', []))
        self.base_dn = getattr(meta, 'base_dn', None)
        self.object_name = name

    def add_field(self, field):
        self._fields[field.name] = field

    def get_field_by_name(self, name):
        return self._fields[name]

    def get_all_field_names(self):
        return self._fields.keys()

    @property
    def fields(self):
        return self._fields.values()

