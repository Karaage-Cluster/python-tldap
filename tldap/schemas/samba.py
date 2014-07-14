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


# Samba

class sambaSamAccount(tldap.base.LDAPobject):
    uid = tldap.fields.CharField(required=True)
    sambaSID = tldap.fields.CharField(required=True)
    cn = tldap.fields.CharField()
    sambaLMPassword = tldap.fields.CharField()
    sambaNTPassword = tldap.fields.CharField()
    sambaPwdLastSet = tldap.fields.SecondsSinceEpochField()
    sambaLogonTime = tldap.fields.SecondsSinceEpochField()
    sambaLogoffTime = tldap.fields.SecondsSinceEpochField()
    sambaKickoffTime = tldap.fields.SecondsSinceEpochField()
    sambaPwdCanChange = tldap.fields.SecondsSinceEpochField()
    sambaPwdMustChange = tldap.fields.SecondsSinceEpochField()
    sambaAcctFlags = tldap.fields.CharField()
    displayName = tldap.fields.CharField()
    sambaHomePath = tldap.fields.CharField()
    sambaHomeDrive = tldap.fields.CharField()
    sambaLogonScript = tldap.fields.CharField()
    sambaProfilePath = tldap.fields.CharField()
    description = tldap.fields.CharField()
    sambaUserWorkstations = tldap.fields.CharField()
    sambaPrimaryGroupSID = tldap.fields.CharField()
    sambaDomainName = tldap.fields.CharField()
    sambaMungedDial = tldap.fields.CharField()
    sambaBadPasswordCount = tldap.fields.CharField()
    sambaBadPasswordTime = tldap.fields.CharField()
    sambaPasswordHistory = tldap.fields.CharField()
    sambaLogonHours = tldap.fields.CharField()

    class Meta:
        object_classes = set(['sambaSamAccount'])


class sambaGroupMapping(tldap.base.LDAPobject):
    gidNumber = tldap.fields.IntegerField(required=True)
    sambaSID = tldap.fields.CharField(required=True)
    sambaGroupType = tldap.fields.IntegerField(required=True)
    displayName = tldap.fields.CharField()
    sambaSIDList = tldap.fields.CharField()

    class Meta:
        object_classes = set(['sambaGroupMapping'])
