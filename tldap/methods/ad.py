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

class adUserMixin(object):
    @classmethod
    def __unicode__(cls, self):
        return u"ADU:%s"%(self.displayName or self.cn)

    @classmethod
    def set_defaults(cls, self):
        self.userAccountControl = 512

    @classmethod
    def pre_create(cls, self, master):
        assert self.objectSid is None
        if master is not None:
            self.sAMAccountName = getattr(master, "sAMAccountName", None)
        if self.sAMAccountName is None:
            self.sAMAccountName = self.uid

        # we can't set the primary group on initial creation, set this later
        self.tmp_primary_group = self.primary_group.get_obj()
        self.primary_group = None

    @classmethod
    def post_create(cls, self, master):
        # AD sets this automagically
        using = self._alias
        self._db_values[using]["primaryGroupID"] = [ 513, ]

        # set our desired primary group
        self.secondary_groups.add(self.tmp_primary_group)
        self.primary_group = self.tmp_primary_group
        self.save()

    @classmethod
    def is_locked(cls, self):
        return self.userAccountControl & 0x2

    @classmethod
    def lock(cls, self):
        self.userAccountControl = self.userAccountControl | 0x2

    @classmethod
    def unlock(cls, self):
        self.userAccountControl = self.userAccountControl & 0xFFFFFFFD

    @classmethod
    def change_password(cls, self, password):
        self.userPassword = None
        self.unicodePwd = '"' + password + '"'
        self.force_replace.add('unicodePwd')


class adGroupMixin(object):
    @classmethod
    def __unicode__(cls, self):
        return u"ADG:%s"%(self.displayName or self.cn)

    @classmethod
    def pre_save(cls, self):
        if self.displayName is None:
            self.displayName = self.cn
