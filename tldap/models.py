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
        object_classes = { 'pwdPolicy' }

class posixGroup(tldap.base.LDAPobject):
    cn = tldap.fields.CharField(required=True)
    gidNumber = tldap.fields.IntegerField(required=True)
    userPassword = tldap.fields.CharField()
    memberUid = tldap.fields.CharField(max_instances=None)
    description = tldap.fields.CharField()

    class Meta:
        object_classes = { 'posixGroup', }

# Directory Server

class Meow(tldap.base.LDAPobject):
    nsAccountLock = tldap.fields.CharField()

# Samba

class sambaSamAccount(tldap.base.LDAPobject):
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

class sambaGroupMapping(tldap.base.LDAPobject):
    # posixGroup
    gidNumber = tldap.fields.IntegerField(required=True)
    sambaSID = tldap.fields.CharField(required=True)
    sambaGroupType = tldap.fields.CharField(required=True)
    displayName = tldap.fields.CharField()
    sambaSIDList = tldap.fields.CharField()

    class Meta:
        object_classes = { 'sambaGroupMapping', }

class eduPerson(tldap.base.LDAPobject):
    eduPersonAffiliation = tldap.fields.CharField()
    eduPersonNickname = tldap.fields.CharField()
    eduPersonOrgDN = tldap.fields.CharField()
    eduPersonOrgUnitDN = tldap.fields.CharField()
    eduPersonPrimaryAffiliation = tldap.fields.CharField()
    eduPersonPrincipalName = tldap.fields.CharField()
    eduPersonEntitlement = tldap.fields.CharField()
    eduPersonPrimaryOrgUnitDN = tldap.fields.CharField()
    eduPersonScopedAffiliation = tldap.fields.CharField()
    eduPersonTargetedID = tldap.fields.CharField()
    eduPersonAssurance = tldap.fields.CharField()

    class Meta:
        object_classes = { 'eduPerson', }

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
        object_classes = { 'auEduPerson', }

# Active Directory

class user(tldap.base.LDAPobject):
    givenName = tldap.fields.CharField()
    loginShell = tldap.fields.CharField()
    mail = tldap.fields.CharField()
    o = tldap.fields.CharField()
    sAMAccountName = tldap.fields.CharField(required=True)
    sn = tldap.fields.CharField()
    telephoneNumber = tldap.fields.CharField()
    title = tldap.fields.CharField()
    unicodePwd = tldap.fields.CharField()
    unixHomeDirectory = tldap.fields.CharField()
    userAccountControl = tldap.fields.IntegerField()

    class Meta:
        object_classes = { 'user', }

class group(tldap.base.LDAPobject):
    cn = tldap.fields.CharField()
    gidNumber = tldap.fields.CharField()
    name = tldap.fields.CharField()
    sAMAccountName = tldap.fields.CharField()

    class Meta:
        object_classes = { 'group', }

########################################################

# standard objects

class std_person(person, organizationalPerson, inetOrgPerson):
    # groups
#    groups = tldap.manager.ManyToManyDescriptor('uid', 'tldap.models.hgroup', 'memberUid', True, "std_users")

    def construct_dn(self):
        return self.rdn_to_dn('uid')

    class Meta:
        base_dn = django.conf.settings.LDAP_USER_BASE
        object_classes = { 'top', }

class std_account(std_person, posixAccount, shadowAccount):
    pass

class std_group(posixGroup):
    # users
    primary_users = tldap.manager.OneToManyDescriptor('gidNumber', std_account, 'gidNumber', "primary_group")
    secondary_users = tldap.manager.ManyToManyDescriptor('memberUid', std_person, 'uid', False, "secondary_groups")

    def construct_dn(self):
        return self.rdn_to_dn('cn')

    class Meta:
        base_dn = django.conf.settings.LDAP_GROUP_BASE
        object_classes = { 'top', }

# pwdPolicy objects

class pp_person(std_person, pwdPolicy):
    def is_locked(self):
        return self.pwdAccountLockedTime is not None

    def lock(self):
        self.pwdAccountLockedTime='000001010000Z'

    def unlock(self):
        self.pwdAccountLockedTime=None


class pp_account(std_account, pwdPolicy):
    def is_locked(self):
        return self.pwdAccountLockedTime is not None

    def lock(self):
        self.pwdAccountLockedTime='000001010000Z'

    def unlock(self):
        self.pwdAccountLockedTime=None

class pp_group(posixGroup):
    # users
    primary_users = tldap.manager.OneToManyDescriptor('gidNumber', pp_account, 'gidNumber', "primary_group")
    secondary_users = tldap.manager.ManyToManyDescriptor('memberUid', pp_person, 'uid', False, "secondary_groups")

    def construct_dn(self):
        return self.rdn_to_dn('cn')

# Active Directory

class ad_person(std_person):
    pass

class ad_account(std_person, user):
    def is_locked(self):
        return self.userAccountControl != 512

    def lock(self):
        self.userAccountControl=514

    def unlock(self):
        self.userAccountControl=512

    def save(self, *args, **kwargs):
        if self.userAccountControl is None:
            self.userAccountControl = 512
        self.sAMAccountName = self.uid
        self.unicodePwd = self.userPassword
        self.unixUserPassword = self.userPassword
        super(ad_account, self).save(*args, **kwargs)

class ad_group(group):
    # users
    primary_users = tldap.manager.OneToManyDescriptor('gidNumber', ad_account, 'gidNumber', "primary_group")
    secondary_users = tldap.manager.ManyToManyDescriptor('memberUid', ad_person, 'uid', False, "secondary_groups")

    def construct_dn(self):
        return self.rdn_to_dn('cn')

    class Meta:
        base_dn = django.conf.settings.LDAP_GROUP_BASE
        object_classes = { 'top', }

    def save(self, *args, **kwargs):
        self.member = [ user.dn for user in self.secondary_users ]
        super(ad_group, self).save(*args, **kwargs)

    class Meta:
        base_dn = django.conf.settings.LDAP_GROUP_BASE
        object_classes = { 'top', }
