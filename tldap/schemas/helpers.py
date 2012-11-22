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

class accountMixin(object):
    def set_free_uidNumber(self):
        model = self.__class__
        uid = None
        for u in model.objects.all():
            if uid is None or u.uidNumber > uid:
                uid = u.uidNumber
        self.uidNumber = uid + 1


class groupMixin(object):
    def set_free_gidNumber(self):
        model = self.__class__
        gid = None
        for g in model.objects.all():
            if gid is None or g.gidNumber > gid:
                gid = g.gidNumber
        self.gidNumber = gid + 1
