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

""" Methods specific for Directory Server 389. """


class passwordObjectMixin(object):
    @classmethod
    def is_locked(cls, self):
        if self.accountUnlockTime is not None:
            return True
        role = self._settings.get("LOCKED_ROLE", None)
        if role is not None and self.nsRoleDN == role:
            return True
        return False

    @classmethod
    def lock(cls, self):
        role = self._settings.get("LOCKED_ROLE", None)
        if role is not None:
            self.nsRoleDN = role
        self.accountUnlockTime = '19700101000000Z'

    @classmethod
    def unlock(cls, self):
        self.nsRoleDN = None
        self.accountUnlockTime = None
