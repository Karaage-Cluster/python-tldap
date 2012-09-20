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
    #telephoneNumber = tldap.fields.CharField()
    facsimileTelephoneNumber = tldap.fields.CharField()
    # +others

    # inetOrgPerson
    givenName = tldap.fields.CharField()
    mail = tldap.fields.CharField()
    manager = tldap.fields.CharField()
    mobile = tldap.fields.CharField()
    o = tldap.fields.CharField()
    photo = tldap.fields.CharField()
    uid = tldap.fields.CharField()
    # +others

    # optional

    class Meta:
        base_dn = django.conf.settings.LDAP_USER_BASE
        object_classes = { 'top', 'person', 'organizationalPerson', 'inetOrgPerson', }

class ldap_account(person):
    loginShell = tldap.fields.CharField()
    homeDirectory = tldap.fields.CharField()
    gecos = tldap.fields.CharField()

    class Meta:
        base_dn = django.conf.settings.LDAP_USER_BASE
        object_classes = { 'posixAccount', 'shadowAccount', }

class ldap_pwd_account(ldap_account):
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

