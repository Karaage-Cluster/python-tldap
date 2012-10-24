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

import tldap.models
import tldap.ldap_passwd
import tldap.manager

import time
import datetime

import django.conf

# standard objects

class std_person(tldap.models.person, tldap.models.organizationalPerson, tldap.models.inetOrgPerson):
    # groups
#    secondary_groups = tldap.manager.ManyToManyDescriptor('uid', 'tldap.models.hgroup', 'memberUid', True)

    class Meta:
        base_dn = django.conf.settings.LDAP_USER_BASE
        object_classes = { 'top', }
        pk = 'uid'

    def __unicode__(self):
        return u"P:%s"%self.cn

    def check_password(self, password):
        return tldap.connection.check_password(self.dn, password)

    def change_password(self, password, scheme):
        if isinstance(password, unicode):
            password = password.encode()

        up = tldap.ldap_passwd.UserPassword()
        self.userPassword = up.encodePassword(password, scheme)
        #self.sambaNTPassword=smbpasswd.nthash(password)
        #self.sambaLMPassword=smbpasswd.lmhash(password)
        #self.sambaPwdMustChange=None
        # unicode_password = unicode("\"" + str(password) + "\"", "iso-8859-1").encode("utf-16-le")
        # self.unicodePwd=unicode_password
        self.sambaPwdLastSet=str(int(time.mktime(datetime.datetime.now().timetuple())))

    def save(self, *args, **kwargs):
        if self.cn is None:
            self.cn = u"%s %s" % (self.givenName, self.sn)
        super(std_person, self).save(*args, **kwargs)

    managed_by = tldap.manager.ManyToOneDescriptor('manager', 'tldap.models.std_person', 'dn')
    manager_of = tldap.manager.OneToManyDescriptor('dn', 'tldap.models.std_person', 'manager')

class std_account(std_person, tldap.models.posixAccount, tldap.models.shadowAccount):

    def __unicode__(self):
        return u"A:%s"%self.cn

    def save(self, *args, **kwargs):
        if self.uidNumber is None:
            uid = None
            for group in std_account.objects.all():
                if uid is None or group.uidNumber > uid:
                    uid = group.uidNumber
            self.uidNumber = uid + 1
        super(std_account, self).save(*args, **kwargs)

class std_group(tldap.models.posixGroup):
    # accounts
    primary_accounts = tldap.manager.OneToManyDescriptor('gidNumber', std_account, 'gidNumber', "primary_group")
    secondary_people = tldap.manager.ManyToManyDescriptor('memberUid', std_person, 'uid', False, "secondary_groups")
    secondary_accounts = tldap.manager.ManyToManyDescriptor('memberUid', std_account, 'uid', False, "secondary_groups")

    class Meta:
        base_dn = django.conf.settings.LDAP_GROUP_BASE
        object_classes = { 'top', }
        pk = 'cn'

    def __unicode__(self):
        return u"G:%s"%self.cn

    def save(self, *args, **kwargs):
        if self.gidNumber is None:
            gid = None
            for group in std_group.objects.all():
                if gid is None or group.gidNumber > gid:
                    gid = group.gidNumber
            self.gidNumber = gid + 1
        super(std_group, self).save(*args, **kwargs)

# pwdPolicy objects

class pp_person(std_person, tldap.models.pwdPolicy):
    def is_locked(self):
        return self.pwdAccountLockedTime is not None

    def lock(self):
        self.pwdAccountLockedTime='000001010000Z'

    def unlock(self):
        self.pwdAccountLockedTime=None

    def save(self, *args, **kwargs):
        self.pwdAttribute = 'userPassword'
        super(pp_person, self).save(*args, **kwargs)


class pp_account(std_account, tldap.models.pwdPolicy):
    def is_locked(self):
        return self.pwdAccountLockedTime is not None

    def lock(self):
        self.pwdAccountLockedTime='000001010000Z'

    def unlock(self):
        self.pwdAccountLockedTime=None

    def save(self, *args, **kwargs):
        self.pwdAttribute = 'userPassword'
        super(pp_account, self).save(*args, **kwargs)

class pp_group(std_group):
    # accounts
    primary_accounts = tldap.manager.OneToManyDescriptor('gidNumber', pp_account, 'gidNumber', "primary_group")
    secondary_people = tldap.manager.ManyToManyDescriptor('memberUid', pp_person, 'uid', False, "secondary_groups")
    secondary_accounts = tldap.manager.ManyToManyDescriptor('memberUid', pp_account, 'uid', False, "secondary_groups")

# Active Directory

class ad_person(std_person):
    pass

class ad_account(std_person, tldap.models.user):
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
        # self.unicodePwd = self.userPassword
        # self.unixUserPassword = self.userPassword
        super(ad_account, self).save(*args, **kwargs)

class ad_group(tldap.models.group):
    # accounts
    primary_accounts = tldap.manager.OneToManyDescriptor('gidNumber', ad_account, 'gidNumber', "primary_group")
    secondary_people = tldap.manager.ManyToManyDescriptor('memberUid', ad_person, 'uid', False, "secondary_groups")
    secondary_accounts = tldap.manager.ManyToManyDescriptor('memberUid', ad_account, 'uid', False, "secondary_groups")

    class Meta:
        base_dn = django.conf.settings.LDAP_GROUP_BASE
        object_classes = { 'top', }
        pk = 'cn'

    def save(self, *args, **kwargs):
        self.member = [ user.dn for user in self.secondary_people ]
        super(ad_group, self).save(*args, **kwargs)

    class Meta:
        base_dn = django.conf.settings.LDAP_GROUP_BASE
        object_classes = { 'top', }


account = pp_account
group = pp_group
