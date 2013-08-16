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

import tldap.methods.ldap_passwd

class passwordObjectMixin(object):
    @classmethod
    def is_locked(cls, self):
        return self.accountUnlockTime is not None

    @classmethod
    def lock(cls, self):
        print "LOCKING NOWQ"
        self.accountUnlockTime='19700101000000Z'

    @classmethod
    def unlock(cls, self):
        self.accountUnlockTime=None
