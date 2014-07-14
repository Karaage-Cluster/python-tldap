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


class eduPerson(tldap.base.LDAPobject):
    eduPersonAffiliation = tldap.fields.CharField()
    eduPersonNickname = tldap.fields.CharField()
    eduPersonOrgDN = tldap.fields.CharField()
    eduPersonOrgUnitDN = tldap.fields.CharField()
    eduPersonPrimaryAffiliation = tldap.fields.CharField()
    eduPersonPrincipalName = tldap.fields.CharField()
    eduPersonEntitlement = tldap.fields.CharField(max_instances=None)
    eduPersonPrimaryOrgUnitDN = tldap.fields.CharField()
    eduPersonScopedAffiliation = tldap.fields.CharField()
    eduPersonTargetedID = tldap.fields.CharField()
    eduPersonAssurance = tldap.fields.CharField()

    class Meta:
        object_classes = set(['eduPerson'])


class auEduPerson(tldap.base.LDAPobject):
    auEduPersonID = tldap.fields.CharField()
    auEduPersonSalutation = tldap.fields.CharField()
    auEduPersonPreferredGivenName = tldap.fields.CharField()
    auEduPersonPreferredSurname = tldap.fields.CharField()
    auEduPersonExpiryDate = tldap.fields.CharField()
    auEduPersonType = tldap.fields.CharField()
    auEduPersonSubType = tldap.fields.CharField()
    auEduPersonEmailAddress = tldap.fields.CharField()
    auEduPersonLibraryBarCodeNumber = tldap.fields.CharField()
    auEduPersonLibraryPIN = tldap.fields.CharField()
    auEduPersonActiveUnit = tldap.fields.CharField()
    member = tldap.fields.CharField()
    auEduPersonAffiliation = tldap.fields.CharField()
    auEduPersonLegalName = tldap.fields.CharField()
    auEduPersonAuthenticationLOA = tldap.fields.CharField()
    auEduPersonIdentityLOA = tldap.fields.CharField()
    auEduPersonSharedToken = tldap.fields.CharField()

    class Meta:
        object_classes = set(['auEduPerson'])
