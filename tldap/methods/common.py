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

""" Methods for common attributes. """

import six
from django.utils.encoding import python_2_unicode_compatible
import tldap
import tldap.methods.models
import tldap.ldap_passwd as ldap_passwd
import datetime


@python_2_unicode_compatible
class personMixin(object):
    @classmethod
    def __str__(cls, self):
        return six.u("P:%s") % (self.displayName or self.cn)

    @classmethod
    def check_password(cls, self, password):
        using = self._alias
        return tldap.connections[using].check_password(self.dn, password)

    @classmethod
    def pre_save(cls, self):
        self.displayName = '%s %s' % (self.givenName, self.sn)
        self.cn = self.displayName

    @classmethod
    def change_password(cls, self, password):
        self.userPassword = ldap_passwd.encode_password(password)


@python_2_unicode_compatible
class accountMixin(object):
    @classmethod
    def set_free_uidNumber(cls, self):
        using = self._alias
        model = self.__class__
        settings = self._settings
        scheme = settings.get('NUMBER_SCHEME', using)
        first = settings.get('UID_FIRST', 10000)
        self.uidNumber = tldap.methods.models.Counters.get_and_increment(
            scheme, "uidNumber", first,
            lambda n: len(
                model.objects.using(using, settings)
                .filter(uidNumber=n)) == 0)

    @classmethod
    def __str__(cls, self):
        return six.u("%s") % (self.displayName or self.cn)

    @classmethod
    def setup_from_master(cls, self, master):
        self.uidNumber = master.uidNumber

    @classmethod
    def pre_add(cls, self):
        if self.loginShell is None:
            self.loginShell = '/bin/bash'
        if self.uidNumber is None:
            cls.set_free_uidNumber(self)
        if self.unixHomeDirectory is None and self.uid is not None:
            self.unixHomeDirectory = '/home/%s' % self.uid

    @classmethod
    def pre_save(cls, self):
        self.gecos = '%s %s' % (self.givenName, self.sn)

    @classmethod
    def pre_delete(cls, self):
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
        self.shadowLastChange = datetime.datetime.now().date()


@python_2_unicode_compatible
class groupMixin(object):
    # Note standard posixGroup objectClass has no displayName attribute

    @classmethod
    def set_free_gidNumber(cls, self):
        using = self._alias
        model = self.__class__
        settings = self._settings
        scheme = settings.get('NUMBER_SCHEME', using)
        first = settings.get('GID_FIRST', 10000)
        self.gidNumber = tldap.methods.models.Counters.get_and_increment(
            scheme, "gidNumber", first,
            lambda n: len(
                model.objects.using(using, settings)
                .filter(gidNumber=n)) == 0)

    @classmethod
    def __str__(cls, self):
        return six.u("%s") % self.cn

    @classmethod
    def setup_from_master(cls, self, master):
        self.gidNumber = master.gidNumber

    @classmethod
    def pre_add(cls, self):
        if self.gidNumber is None:
            cls.set_free_gidNumber(self)

    @classmethod
    def pre_save(cls, self):
        if self.description is None:
            self.description = self.cn
