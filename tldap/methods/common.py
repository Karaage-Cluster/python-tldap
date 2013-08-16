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

import tldap
import tldap.methods.models
import tldap.methods.ldap_passwd
import datetime


class personMixin(object):
    @classmethod
    def __unicode__(cls, self):
        return u"P:%s"%(self.displayName or self.cn)

    @classmethod
    def check_password(cls, self, password):
        using = self._alias
        return tldap.connections[using].check_password(self.dn, password)

    @classmethod
    def pre_save(cls, self, using):
        self.displayName = '%s %s' % (self.givenName, self.sn)
        self.cn = self.displayName

    @classmethod
    def change_password(cls, self, password):
        up = tldap.methods.ldap_passwd.UserPassword()
        self.userPassword = up.encodePassword(password, "ssha")


class accountMixin(object):
    @classmethod
    def set_free_uidNumber(cls, self, using):
        model = self.__class__
        settings = self._settings
        scheme = settings.get('NUMBER_SCHEME', using)
        first = settings.get('UID_FIRST', 10000)
        self.uidNumber =  tldap.methods.models.Counters.get_and_increment(
                scheme, "uidNumber", first,
                lambda n: len(
                    model.objects.using(using, settings)
                    .filter(uidNumber = n)) == 0)

    @classmethod
    def __unicode__(cls, self):
        return u"%s"%(self.displayName or self.cn)

    @classmethod
    def setup_from_master(cls, self, master):
        self.uidNumber = master.uidNumber

    @classmethod
    def pre_add(cls, self, using):
        if self.loginShell is None:
            self.loginShell = '/bin/bash'
        if self.uidNumber is None:
            cls.set_free_uidNumber(self, using)
        if self.unixHomeDirectory is None and self.uid is not None:
            self.unixHomeDirectory =  '/home/%s' % self.uid

    @classmethod
    def pre_save(cls, self, using):
        self.gecos = '%s %s' % (self.givenName, self.sn)

    @classmethod
    def pre_delete(cls, self, using):
        self.manager_of.clear()

    @classmethod
    def lock(cls, self):
        if self.loginShell is None:
            return
        if not self.loginShell.startswith("/locked"):
            self.loginShell = '/locked' + self.loginShell

    @classmethod
    def unlock(cls, self):
        if self.loginShell is None:
            return
        if self.loginShell.startswith("/locked"):
            self.loginShell = self.loginShell[7:]


class shadowMixin(object):

    @classmethod
    def change_password(cls, self, password):
        self.shadowLastChange=datetime.datetime.now().date()


class groupMixin(object):
    # Note standard posixGroup objectClass has no displayName attribute

    @classmethod
    def set_free_gidNumber(cls, self, using):
        model = self.__class__
        settings = self._settings
        scheme = settings.get('NUMBER_SCHEME', using)
        first = settings.get('GID_FIRST', 10000)
        self.gidNumber =  tldap.methods.models.Counters.get_and_increment(
                scheme, "gidNumber", first,
                lambda n: len(
                    model.objects.using(using, settings)
                    .filter(gidNumber = n)) == 0)

    @classmethod
    def __unicode__(cls, self):
        return u"%s"%self.cn

    @classmethod
    def setup_from_master(cls, self, master):
        self.gidNumber = master.gidNumber

    @classmethod
    def pre_add(cls, self, using):
        if self.gidNumber is None:
            cls.set_free_gidNumber(self, using)

    @classmethod
    def pre_save(cls, self, using):
        if self.description is None:
            self.description = self.cn


