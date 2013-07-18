# Copyright 2012-2013 VPAC
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

import tldap.base


class baseMixin(tldap.base.LDAPobject):
    mixin_list = []

    def change_password(self, password):
        for mixin in self.mixin_list:
            if hasattr(mixin, 'change_password'):
                mixin.change_password(self, password)

    def set_defaults(self):
        for mixin in self.mixin_list:
            if hasattr(mixin, 'set_defaults'):
                mixin.set_defaults(self)

    def pre_create(self, master):
        for mixin in self.mixin_list:
            if hasattr(mixin, 'pre_create'):
                mixin.pre_create(self, master)

    def post_create(self, master):
        for mixin in self.mixin_list:
            if hasattr(mixin, 'post_create'):
                mixin.post_create(self, master)

    def pre_save(self):
        for mixin in self.mixin_list:
            if hasattr(mixin, 'pre_save'):
                mixin.pre_save(self)

    def pre_delete(self):
        for mixin in self.mixin_list:
            if hasattr(mixin, 'pre_delete'):
                mixin.pre_delete(self)

    def lock(self):
        for mixin in self.mixin_list:
            if hasattr(mixin, 'lock'):
                mixin.lock(self)

    def unlock(self):
        for mixin in self.mixin_list:
            if hasattr(mixin, 'unlock'):
                mixin.unlock(self)

    def check_password(self, password):
        locked = True
        num = 0

        if self.is_locked():
            return False

        for mixin in self.mixin_list:
            if hasattr(mixin, 'check_password'):
                num = num + 1
                if not mixin.check_password(self, password):
                    locked = False

        if num == 0:
            locked = False

        return locked

    def is_locked(self):
        locked = True

        for mixin in self.mixin_list:
            if hasattr(mixin, 'is_locked'):
                if not mixin.is_locked(self):
                    locked = False

        return locked

    def __unicode__(self):
        for mixin in reversed(self.mixin_list):
            if hasattr(mixin, '__unicode__'):
                return mixin.__unicode__(self)


