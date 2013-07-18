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

import django.conf
import base64

try:
    from hashlib import sha
except:
    from sha import sha

class shibbolethMixin(object):

    @classmethod
    def _generate_shared_token(cls, self):
        uid = self.uid
        entityID = django.conf.settings.SHIBBOLETH_URL
        salt = django.conf.settings.SHIBBOLETH_SALT
        return base64.urlsafe_b64encode(sha(uid + entityID + salt).digest())[:-1]

    @classmethod
    def pre_create(cls, self, master):
        assert self.auEduPersonSharedToken is None
        self.auEduPersonSharedToken = cls._generate_shared_token(self)

    @classmethod
    def lock(cls, self):
        self.eduPersonAffiliation = 'affiliate'

    @classmethod
    def unlock(cls, self):
        self.edupersonaffiliation = 'staff'

