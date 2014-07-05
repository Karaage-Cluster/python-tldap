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

import six
from django.utils.encoding import python_2_unicode_compatible

import tldap
import tldap.schemas.rfc as rfc
import tldap.manager

# standard objects


@python_2_unicode_compatible
class person(tldap.base.LDAPobject):
    schema_list = [rfc.person, rfc.organizationalPerson, rfc.inetOrgPerson]

    class Meta:
        base_dn_setting = "LDAP_ACCOUNT_BASE"
        object_classes = set(['top'])
        pk = 'uid'

    def __str__(self):
        return six.u("P:%s") % self.cn

    def save(self, *args, **kwargs):
        if self.cn is None:
            self.cn = six.u("%s %s") % (self.givenName, self.sn)
        super(person, self).save(*args, **kwargs)

    managed_by = tldap.manager.ManyToOneDescriptor(
        this_key='manager',
        linked_cls='tldap.tests.schemas.person', linked_key='dn')
    manager_of = tldap.manager.OneToManyDescriptor(
        this_key='dn',
        linked_cls='tldap.tests.schemas.person', linked_key='manager')


@python_2_unicode_compatible
class account(person):
    schema_list = [rfc.posixAccount, rfc.shadowAccount]

    def __str__(self):
        return six.u("A:%s") % self.cn

    def save(self, *args, **kwargs):
        if self.uidNumber is None:
            uid = None
            for u in account.objects.all():
                if uid is None or u.uidNumber > uid:
                    uid = u.uidNumber
            self.uidNumber = uid + 1
        super(account, self).save(*args, **kwargs)


@python_2_unicode_compatible
class group(tldap.base.LDAPobject):
    schema_list = [rfc.posixGroup]

    primary_accounts = tldap.manager.OneToManyDescriptor(
        this_key='gidNumber', linked_cls=account, linked_key='gidNumber',
        related_name="primary_group")
    secondary_people = tldap.manager.ManyToManyDescriptor(
        this_key='memberUid', linked_cls=person, linked_key='uid',
        linked_is_p=False, related_name="secondary_groups")
    secondary_accounts = tldap.manager.ManyToManyDescriptor(
        this_key='memberUid', linked_cls=account, linked_key='uid',
        linked_is_p=False, related_name="secondary_groups")

    class Meta:
        base_dn_setting = "LDAP_GROUP_BASE"
        object_classes = set(['top'])
        pk = 'cn'

    def __str__(self):
        return six.u("%s") % self.cn

    def save(self, *args, **kwargs):
        if self.gidNumber is None:
            gid = None
            for g in group.objects.all():
                if gid is None or g.gidNumber > gid:
                    gid = g.gidNumber
            self.gidNumber = gid + 1
        super(group, self).save(*args, **kwargs)
