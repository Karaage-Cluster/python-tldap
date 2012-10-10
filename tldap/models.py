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

#import copy

import django.conf
#import ldap
#import ldap.filter


class person(tldap.base.LDAPobject):
    objectClass = tldap.fields.CharField(required=True, max_instances=None)

    # person
    sn = tldap.fields.CharField(required=True)
    cn = tldap.fields.CharField(required=True)
    userPassword = tldap.fields.CharField()
    telephoneNumber = tldap.fields.CharField()
    seeAlso = tldap.fields.CharField()
    description = tldap.fields.CharField()

    # organizationalPerson
    title = tldap.fields.CharField()
    x121Address = tldap.fields.CharField()
    registeredAddresss = tldap.fields.CharField()
    destinationIndicator = tldap.fields.CharField()
    preferredDeliveryMethod = tldap.fields.CharField()
    telexNumber = tldap.fields.CharField()
    teletexTerminalIdentifier = tldap.fields.CharField()
    #telephoneNumber = tldap.fields.CharField()
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

    # inetOrgPerson
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

    def construct_dn(self):
        return self.rdn_to_dn('uid')

    class Meta:
        base_dn = django.conf.settings.LDAP_USER_BASE
        object_classes = { 'top', 'person', 'organizationalPerson', 'inetOrgPerson', }

class posix_account(person):
    loginShell = tldap.fields.CharField()
    homeDirectory = tldap.fields.CharField()
    gecos = tldap.fields.CharField()

    class Meta:
        base_dn = django.conf.settings.LDAP_USER_BASE
        object_classes = { 'posixAccount', 'shadowAccount', }

class samba_account(posix_account):
    # sambaSamAccount
    # uid = tldap.fields.CharField(required=True)
    sambaSID = tldap.fields.CharField(required=True)
    # cn = tldap.fields.CharField()
    sambaLMPassword = tldap.fields.CharField()
    sambaNTPassword = tldap.fields.CharField()
    sambaPwdLastSet = tldap.fields.CharField()
    sambaLogonTime = tldap.fields.CharField()
    sambaLogoffTime = tldap.fields.CharField()
    sambaKickoffTime = tldap.fields.CharField()
    sambaPwdCanChange = tldap.fields.CharField()
    sambaPwdMustChange = tldap.fields.CharField()
    sambaAcctFlags = tldap.fields.CharField()
    # displayName = tldap.fields.CharField()
    sambaHomePath = tldap.fields.CharField()
    sambaHomeDrive = tldap.fields.CharField()
    sambaLogonScript = tldap.fields.CharField()
    sambaProfilePath = tldap.fields.CharField()
    # description = tldap.fields.CharField()
    sambaUserWorkstations = tldap.fields.CharField()
    sambaPrimaryGroupSID = tldap.fields.CharField()
    sambaDomainName = tldap.fields.CharField()
    sambaMungedDial = tldap.fields.CharField()
    sambaBadPasswordCount = tldap.fields.CharField()
    sambaBadPasswordTime = tldap.fields.CharField()
    sambaPasswordHistory = tldap.fields.CharField()
    sambaLogonHours = tldap.fields.CharField()

    class Meta:
        base_dn = django.conf.settings.LDAP_USER_BASE
        object_classes = { 'sambaSamAccount', }

class posix_pwd_account(posix_account):
    pwdAccountLockedTime = tldap.fields.CharField(required=True)

    class Meta:
        base_dn = django.conf.settings.LDAP_USER_BASE
        object_classes = { '???' }

class ad_account(person):
    sAMAccountName = tldap.fields.CharField(required=True)
    unicodePwd = tldap.fields.CharField()
    loginShell = tldap.fields.CharField()
    unixHomeDirectory = tldap.fields.CharField()

    class Meta:
        base_dn = django.conf.settings.LDAP_USER_BASE
        object_classes = { 'user', }

class posix_group(tldap.base.LDAPobject):
    objectClass = tldap.fields.CharField(required=True, max_instances=None)

    # posixGroup
    cn = tldap.fields.CharField(required=True)
    gidNumber = tldap.fields.CharField(required=True)
    userPassword = tldap.fields.CharField()
    memberUid = tldap.fields.CharField()
    description = tldap.fields.CharField()

    class Meta:
        base_dn = django.conf.settings.LDAP_GROUP_BASE
        object_classes = { 'posixGroup', }

class samba_group(posix_group):
    # posixGroup
    # gidNumber = tldap.fields.CharField(required=True)
    sambaSID = tldap.fields.CharField(required=True)
    sambaGroupType = tldap.fields.CharField(required=True)
    displayName = tldap.fields.CharField()
    sambaSIDList = tldap.fields.CharField()

    class Meta:
        base_dn = django.conf.settings.LDAP_GROUP_BASE
        object_classes = { 'sambaGroupMapping', }

###########
# TESTING #
###########
#posixAccount = ldap_account

#pa = posixAccount()
#print [ i.name for i in pa._meta.fields ]
#pa.dn = "uid=brian,ou=People,dc=nodomain"
#pa.cn = "Brian May"
#pa.sn = "May"
#pa.save()

#qs = posixAccount.objects.filter(uid='brian')
#print "qs", qs
#for i in posixAccount.objects.filter(uid='brian'):
#    for attr in dir(i):
#        if attr != "objects":
#            print "obj.%s = %s" % (attr, getattr(i, attr))

#a = posixAccount.objects.get(uid='brian')
#a.description = [ "test only" ]
#a.save()

