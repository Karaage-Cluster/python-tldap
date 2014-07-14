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

""" Methods for Shibboleth specific attributes. """

import base64

try:
    from hashlib import sha1 as sha
except:
    from sha import sha


class shibbolethMixin(object):

    @classmethod
    def _generate_shared_token(cls, self):
        uid = self.uid
        settings = self._settings
        entityID = settings['SHIBBOLETH_URL']
        salt = settings['SHIBBOLETH_SALT']
        return base64.urlsafe_b64encode(
            sha(uid + entityID + salt).digest())[:-1]

    @classmethod
    def pre_add(cls, self):
        assert self.auEduPersonSharedToken is None
        self.auEduPersonSharedToken = cls._generate_shared_token(self)

    @classmethod
    def lock(cls, self):
        self.eduPersonAffiliation = 'affiliate'

    @classmethod
    def unlock(cls, self):
        self.edupersonaffiliation = 'staff'
