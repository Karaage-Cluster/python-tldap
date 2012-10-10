# Copyright 2012 VPAC
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
import tldap.manager

import django.conf

#    objectClass = tldap.fields.CharField(required=True, max_instances=None)

class organizationalUnit(tldap.base.LDAPobject):
    ou = tldap.fields.CharField(required=True)
    userPassword = tldap.fields.CharField()
    searchGuide = tldap.fields.CharField()
    seeAlso = tldap.fields.CharField()
    businessCategory = tldap.fields.CharField()
    x121Address = tldap.fields.CharField()
    registeredAddress = tldap.fields.CharField()
    destinationIndicator = tldap.fields.CharField()
    preferredDeliveryMethod = tldap.fields.CharField()
    telexNumber = tldap.fields.CharField()
    teletexTerminalIdentifier = tldap.fields.CharField()
    telephoneNumber = tldap.fields.CharField()
    internationaliSDNNumber = tldap.fields.CharField()
    facsimileTelephoneNumber = tldap.fields.CharField()
    street = tldap.fields.CharField()
    postOfficeBox = tldap.fields.CharField()
    postalCode = tldap.fields.CharField()
    postalAddress = tldap.fields.CharField()
    physicalDeliveryOfficeName = tldap.fields.CharField()
    st = tldap.fields.CharField()
    l = tldap.fields.CharField()
    description = tldap.fields.CharField()

    def construct_dn(self):
        return self.rdn_to_dn('dc')

    class Meta:
        object_classes = { 'organizationalUnit', }

class person(tldap.base.LDAPobject):
    sn = tldap.fields.CharField(required=True)
    cn = tldap.fields.CharField(required=True)
    userPassword = tldap.fields.CharField()
    telephoneNumber = tldap.fields.CharField()
    seeAlso = tldap.fields.CharField()
    description = tldap.fields.CharField()

    class Meta:
        object_classes = { 'person', }

class organizationalPerson(tldap.base.LDAPobject):
    title = tldap.fields.CharField()
    x121Address = tldap.fields.CharField()
    registeredAddresss = tldap.fields.CharField()
    destinationIndicator = tldap.fields.CharField()
    preferredDeliveryMethod = tldap.fields.CharField()
    telexNumber = tldap.fields.CharField()
    teletexTerminalIdentifier = tldap.fields.CharField()
    telephoneNumber = tldap.fields.CharField()
    internationaliSDNNumber = tldap.fields.CharField()
    facsimileTelephoneNumber = tldap.fields.CharField()
    street = tldap.fields.CharField()
    postOfficeBox = tldap.fields.CharField()
    postalCode = tldap.fields.CharField()
    postalAddress = tldap.fields.CharField()
    physicalDeliveryOfficeName = tldap.fields.CharField()
    ou = tldap.fields.CharField()
    st = tldap.fields.CharField()
    l = tldap.fields.CharField()

    class Meta:
        object_classes = { 'organizationalPerson', }

class inetOrgPerson(tldap.base.LDAPobject):
    audio = tldap.fields.CharField()
    businessCategory = tldap.fields.CharField()
    carLicense = tldap.fields.CharField()
    departmentNumber = tldap.fields.CharField()
    displayName = tldap.fields.CharField()
    employeeNumber = tldap.fields.CharField()
    employeeType = tldap.fields.CharField()
    givenName = tldap.fields.CharField()
    homePhone = tldap.fields.CharField()
    homePostalAddress = tldap.fields.CharField()
    initials = tldap.fields.CharField()
    jpegPhoto = tldap.fields.CharField()
    labeledURI = tldap.fields.CharField()
    mail = tldap.fields.CharField()
    manager = tldap.fields.CharField()
    mobile = tldap.fields.CharField()
    o = tldap.fields.CharField()
    pager = tldap.fields.CharField()
    photo = tldap.fields.CharField()
    roomNumber = tldap.fields.CharField()
    secretary = tldap.fields.CharField()
    uid = tldap.fields.CharField()
    userCertificate = tldap.fields.CharField()
    x500uniqueIdentifier = tldap.fields.CharField()
    preferredLanguage = tldap.fields.CharField()
    userSMIMECertificate = tldap.fields.CharField()
    userPKCS12 = tldap.fields.CharField()

    class Meta:
        object_classes = { 'inetOrgPerson', }

class posixAccount(tldap.base.LDAPobject):
    cn = tldap.fields.CharField(required=True)
    uid = tldap.fields.CharField(required=True)
    uidNumber = tldap.fields.IntegerField(required=True)
    gidNumber = tldap.fields.IntegerField(required=True)
    homeDirectory = tldap.fields.CharField(required=True)
    userPassword = tldap.fields.CharField()
    loginShell = tldap.fields.CharField()
    gecos = tldap.fields.CharField()
    description = tldap.fields.CharField()

    class Meta:
        object_classes = { 'posixAccount', }

class shadowAccount(tldap.base.LDAPobject):
    userPassword = tldap.fields.CharField()
    shadowLastChange = tldap.fields.CharField()
    shadowMin = tldap.fields.CharField()
    shadowMax = tldap.fields.CharField()
    shadowWarning = tldap.fields.CharField()
    shadowInactive = tldap.fields.CharField()
    shadowExpire = tldap.fields.CharField()
    shadowFlag = tldap.fields.CharField()
    description = tldap.fields.CharField()

    class Meta:
        object_classes = { 'shadowAccount', }

class sambaSamAccount(tldap.base.LDAPobject):
    # sambaSamAccount
    uid = tldap.fields.CharField(required=True)
    sambaSID = tldap.fields.CharField(required=True)
    cn = tldap.fields.CharField()
    sambaLMPassword = tldap.fields.CharField()
    sambaNTPassword = tldap.fields.CharField()
    sambaPwdLastSet = tldap.fields.CharField()
    sambaLogonTime = tldap.fields.CharField()
    sambaLogoffTime = tldap.fields.CharField()
    sambaKickoffTime = tldap.fields.CharField()
    sambaPwdCanChange = tldap.fields.CharField()
    sambaPwdMustChange = tldap.fields.CharField()
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
        object_classes = { 'sambaSamAccount', }

class posix_pwd_account(tldap.base.LDAPobject):
    pwdAccountLockedTime = tldap.fields.CharField(required=True)

    class Meta:
        object_classes = { '???' }

class ad_user(tldap.base.LDAPobject):
    sAMAccountName = tldap.fields.CharField(required=True)
    unicodePwd = tldap.fields.CharField()
    loginShell = tldap.fields.CharField()
    unixHomeDirectory = tldap.fields.CharField()

    class Meta:
        object_classes = { 'user', }

class posixGroup(tldap.base.LDAPobject):
    cn = tldap.fields.CharField(required=True)
    gidNumber = tldap.fields.IntegerField(required=True)
    userPassword = tldap.fields.CharField()
    memberUid = tldap.fields.CharField(max_instances=None)
    description = tldap.fields.CharField()

    class Meta:
        object_classes = { 'posixGroup', }

class sambaGroupMapping(tldap.base.LDAPobject):
    # posixGroup
    gidNumber = tldap.fields.IntegerField(required=True)
    sambaSID = tldap.fields.CharField(required=True)
    sambaGroupType = tldap.fields.CharField(required=True)
    displayName = tldap.fields.CharField()
    sambaSIDList = tldap.fields.CharField()

    class Meta:
        object_classes = { 'sambaGroupMapping', }



class hperson(person, organizationalPerson, inetOrgPerson):
    # groups
    groups = tldap.manager.FieldDescriptor('uid', 'memberUid', 'tldap.models.hgroup')

    def construct_dn(self):
        return self.rdn_to_dn('uid')

    class Meta:
        base_dn = django.conf.settings.LDAP_USER_BASE

class haccount(hperson, posixAccount, shadowAccount):
    pass

class hgroup(posixGroup):

    # users
    users = tldap.manager.FieldListDescriptor('memberUid', 'uid', hperson)

    def construct_dn(self):
        return self.rdn_to_dn('cn')

    class Meta:
        base_dn = django.conf.settings.LDAP_GROUP_BASE
