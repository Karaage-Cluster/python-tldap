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

import six
import copy


class CaseInsensitiveDict(dict):
    """
    Case insensitve dictionary for searches however preserves the case for
    retrieval.
    """

    def __init__(self, d={}):
        self.lc = {}
        for k, v in six.iteritems(d):
            self.lc[k.lower()] = k
        super(CaseInsensitiveDict, self).__init__(d)

    def __setitem__(self, key, value):
        try:
            old_key = self.lc[key.lower()]
        except KeyError:
            pass
        else:
            if key != old_key:
                super(CaseInsensitiveDict, self).__delitem__(old_key)
        self.lc[key.lower()] = key
        super(CaseInsensitiveDict, self).__setitem__(key, value)

    def __delitem__(self, key):
        key = self.lc[key.lower()]
        del self.lc[key.lower()]
        super(CaseInsensitiveDict, self).__delitem__(key)

    def __getitem__(self, key):
        key = self.lc[key.lower()]
        return super(CaseInsensitiveDict, self).__getitem__(key)

    def __contains__(self, key):
        try:
            key = self.lc[key.lower()]
        except KeyError:
            return False
        else:
            return super(CaseInsensitiveDict, self).__contains__(key)

    def get(self, key, default=None):
        try:
            key = self.lc[key.lower()]
        except KeyError:
            return default
        else:
            return super(CaseInsensitiveDict, self).get(key, default)

    def get_correct_key(self, key):
        return self.lc[key.lower()]

    def __copy__(self):
        clone = self.__class__()
        for k, v in six.iteritems(self):
            clone[k] = v
        return clone

    def __deepcopy__(self, memo):
        clone = self.__class__()
        for k, v in six.iteritems(self):
            clone[k] = copy.deepcopy(v, memo)
        return clone
