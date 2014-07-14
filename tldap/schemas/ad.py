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

import tldap
import tldap.base
import tldap.fields
import tldap.schemas.rfc


class person(tldap.schemas.rfc.person):
    sn = tldap.fields.CharField()
    cn = tldap.fields.CharField()


class posixAccount(tldap.schemas.rfc.posixAccount):
    cn = tldap.fields.CharField()
    uid = tldap.fields.CharField()
    uidNumber = tldap.fields.IntegerField()
    gidNumber = tldap.fields.IntegerField()
    homeDirectory = tldap.fields.CharField()
    unixHomeDirectory = tldap.fields.CharField()


# Active Directory

class user(tldap.base.LDAPobject):
    displayName = tldap.fields.CharField()
    givenName = tldap.fields.CharField()
    loginShell = tldap.fields.CharField()
    mail = tldap.fields.CharField()
    memberOf = tldap.fields.CharField(max_instances=None)
    objectSid = tldap.fields.SidField()
    o = tldap.fields.CharField()
    primaryGroupID = tldap.fields.IntegerField()
    sAMAccountName = tldap.fields.CharField(required=True)
    sn = tldap.fields.CharField()
    telephoneNumber = tldap.fields.CharField()
    title = tldap.fields.CharField()
    unicodePwd = tldap.fields.UnicodeField()
    unixHomeDirectory = tldap.fields.CharField()
    userAccountControl = tldap.fields.IntegerField()

    class Meta:
        object_classes = set(['user'])


class group(tldap.base.LDAPobject):
    cn = tldap.fields.CharField()
    displayName = tldap.fields.CharField()
    gidNumber = tldap.fields.IntegerField()
    member = tldap.fields.CharField(max_instances=None)
    objectSid = tldap.fields.SidField()
    sAMAccountName = tldap.fields.CharField()

    class Meta:
        object_classes = set(['group'])
