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


# Standard LDAP

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

    class Meta:
        object_classes = set(['organizationalUnit'])


class person(tldap.base.LDAPobject):
    sn = tldap.fields.CharField(required=True)
    cn = tldap.fields.CharField(required=True)
    userPassword = tldap.fields.CharField()
    telephoneNumber = tldap.fields.CharField()
    seeAlso = tldap.fields.CharField()
    description = tldap.fields.CharField()

    class Meta:
        object_classes = set(['person'])


class organizationalPerson(tldap.base.LDAPobject):
    title = tldap.fields.CharField()
    x121Address = tldap.fields.CharField()
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
        object_classes = set(['organizationalPerson'])


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
    jpegPhoto = tldap.fields.BinaryField()
    labeledURI = tldap.fields.CharField()
    mail = tldap.fields.CharField()
    manager = tldap.fields.CharField()
    mobile = tldap.fields.CharField()
    o = tldap.fields.CharField()
    pager = tldap.fields.CharField()
    photo = tldap.fields.BinaryField()
    roomNumber = tldap.fields.CharField()
    secretary = tldap.fields.CharField()
    uid = tldap.fields.CharField()
    userCertificate = tldap.fields.BinaryField()
    x500uniqueIdentifier = tldap.fields.CharField()
    preferredLanguage = tldap.fields.CharField()
    userSMIMECertificate = tldap.fields.BinaryField()
    userPKCS12 = tldap.fields.BinaryField()

    class Meta:
        object_classes = set(['inetOrgPerson'])


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
        object_classes = set(['posixAccount'])


class shadowAccount(tldap.base.LDAPobject):
    userPassword = tldap.fields.CharField()
    shadowLastChange = tldap.fields.DaysSinceEpochField()
    shadowMin = tldap.fields.IntegerField()
    shadowMax = tldap.fields.IntegerField()
    shadowWarning = tldap.fields.IntegerField()
    shadowInactive = tldap.fields.IntegerField()
    shadowExpire = tldap.fields.CharField()
    shadowFlag = tldap.fields.CharField()
    description = tldap.fields.CharField()

    class Meta:
        object_classes = set(['shadowAccount'])


class pwdPolicy(tldap.base.LDAPobject):
    pwdAttribute = tldap.fields.CharField(required=True)
    pwdAccountLockedTime = tldap.fields.CharField()
    pwdMinAge = tldap.fields.CharField()
    pwdMaxAge = tldap.fields.CharField()
    pwdInHistory = tldap.fields.CharField()
    pwdCheckQuality = tldap.fields.CharField()
    pwdMinLength = tldap.fields.CharField()
    pwdExpireWarning = tldap.fields.CharField()
    pwdGraceAuthNLimit = tldap.fields.CharField()
    pwdLockout = tldap.fields.CharField()
    pwdLockoutDuration = tldap.fields.CharField()
    pwdMaxFailure = tldap.fields.CharField()
    pwdFailureCountInterval = tldap.fields.CharField()
    pwdMustChange = tldap.fields.CharField()
    pwdAllowUserChange = tldap.fields.CharField()
    pwdSafeModify = tldap.fields.CharField()

    class Meta:
        object_classes = set(['pwdPolicy'])


class posixGroup(tldap.base.LDAPobject):
    cn = tldap.fields.CharField(required=True)
    gidNumber = tldap.fields.IntegerField(required=True)
    userPassword = tldap.fields.CharField()
    memberUid = tldap.fields.CharField(max_instances=None)
    description = tldap.fields.CharField()

    class Meta:
        object_classes = set(['posixGroup'])


class groupOfNames(tldap.base.LDAPobject):
    member = tldap.fields.CharField(max_instances=None, required=True)
    cn = tldap.fields.CharField(required=True)
    businessCategory = tldap.fields.CharField()
    seeAlso = tldap.fields.CharField()
    owner = tldap.fields.CharField()
    ou = tldap.fields.CharField()
    o = tldap.fields.CharField()
    description = tldap.fields.CharField()

    class Meta:
        object_classes = set(['groupOfNames'])
