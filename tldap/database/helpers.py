# Copyright 2018 Brian May
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
""" Various helper functions to aid applications processing schema specific functions. """

import base64
import datetime
from hashlib import sha1
from typing import List

import tldap.exceptions
import tldap.fields
from tldap.database import LdapObject, Changeset, NotLoadedObject, NotLoadedList, \
    NotLoadedListToList, LdapObjectClass, Database
from tldap.dn import str2dn, dn2str
import tldap.ldap_passwd as ldap_passwd


def rdn_to_dn(changes: Changeset, name: str, base_dn: str) -> Changeset:
    """ Convert the rdn to a fully qualified DN for the specified LDAP
    connection.

    :param changes: The changes object to lookup.
    :param name: rdn to convert.
    :param base_dn: The base_dn to lookup.
    :return: fully qualified DN.
    """
    dn = get_value(changes, 'dn')
    if dn is not None:
        return changes

    value = get_value(changes, name)
    if value is None:
        raise tldap.exceptions.ValidationError(
            "Cannot use %s in dn as it is None" % name)
    if isinstance(value, list):
        raise tldap.exceptions.ValidationError(
            "Cannot use %s in dn as it is a list" % name)

    assert base_dn is not None

    split_base = str2dn(base_dn)
    split_new_dn = [[(name, value, 1)]] + split_base

    new_dn = dn2str(split_new_dn)

    return changes.set('dn', new_dn)


def set_object_class(changes: Changeset, object_class: List[str]) -> Changeset:
    if get_value(changes, 'objectClass') is None:
        changes = changes.set('objectClass', object_class)
    return changes


def get_value(changes: Changeset, key: str) -> any:
    if key in changes:
        return changes[key]
    if key in changes._src:
        return changes._src[key]
    return None


# PERSON

def get_fields_person() -> List[tldap.fields.Field]:
    fields = [
        tldap.fields.CharField('cn', required=True),
        tldap.fields.CharField('displayName', required=True),
        tldap.fields.CharField('givenName'),
        tldap.fields.CharField('mail'),
        tldap.fields.CharField('sn', required=True),
        tldap.fields.CharField('telephoneNumber'),
        tldap.fields.CharField('title'),
        tldap.fields.CharField('uid'),
        tldap.fields.CharField('userPassword'),
        tldap.fields.FakeField('password'),
        tldap.fields.FakeField('locked'),
        tldap.fields.FakeField('groups'),
    ]
    return fields


def load_person(python_data: LdapObject, group_table: LdapObjectClass) -> LdapObject:
    python_data = python_data.merge({
        'password': None,
        'groups': NotLoadedList(table=group_table, key="memberUid", value=python_data["uid"])
    })
    return python_data


def save_person(changes: Changeset) -> Changeset:
    d = dict()

    if 'givenName' in changes or 'sn' in changes:
        given_name = get_value(changes, 'givenName')
        sn = get_value(changes, 'sn')

        if given_name is not None and sn is not None:
            d['displayName'] = '%s %s' % (given_name, sn)
            d['cn'] = d['displayName']

    if 'password' in changes:
        d["userPassword"] = ldap_passwd.encode_password(changes['password'])

    if 'groups' in changes:
        groups = get_value(changes, 'groups')
        if len(groups) > 0:
            raise RuntimeError("Cannot register changes in groups on people.")

    return changes.merge(d)


def get_fields_common() -> List[tldap.fields.Field]:
    fields = [
        tldap.fields.FakeField('dn', required=True, max_instances=1),
        tldap.fields.CharField('objectClass', required=True, max_instances=None),
    ]
    return fields


# ACCOUNT

def get_fields_account() -> List[tldap.fields.Field]:
    fields = [
        tldap.fields.CharField('gecos'),
        tldap.fields.CharField('loginShell'),
        tldap.fields.CharField('homeDirectory'),
        tldap.fields.CharField('o'),
        tldap.fields.IntegerField('gidNumber'),
        tldap.fields.IntegerField('uidNumber'),
        tldap.fields.FakeField('primary_group'),
    ]
    return fields


def load_account(python_data: LdapObject, group_table: LdapObjectClass) -> LdapObject:
    d = {
        'locked': python_data['loginShell'].startswith("/locked"),
    }

    if 'gidNumber' in python_data:
        d['primary_group'] = NotLoadedObject(table=group_table, key='gidNumber', value=python_data['gidNumber'])

    python_data = python_data.merge(d)
    return python_data


def save_account(changes: Changeset, database: Database) -> Changeset:
    d = {}
    settings = database.settings

    if get_value(changes, 'locked') is None:
        d['locked'] = False

    if get_value(changes, 'loginShell') is None:
        d['loginShell'] = '/bin/bash'

    changes = changes.merge(d)

    d = {}
    if 'uid' in changes:
        uid = get_value(changes, 'uid')
        home_directory = get_value(changes, 'homeDirectory')

        if uid is not None:
            spec = settings.get('HOME_DIRECTORY', "/home/{uid}s")
            if home_directory is None:
                d['homeDirectory'] = spec.format(uid=uid)

    if 'locked' in changes or 'loginShell' in changes:
        locked = get_value(changes, 'locked')
        login_shell = get_value(changes, 'loginShell')

        if locked is None:
            pass
        elif locked and login_shell is not None:
            if not login_shell.startswith("/locked"):
                d['loginShell'] = '/locked' + login_shell
        elif login_shell is not None:
            if login_shell.startswith("/locked"):
                d['loginShell'] = login_shell[7:]

    fields = ['givenName', 'sn', 'o']
    if any(name in changes for name in fields):
        values = {
            name: get_value(changes, name)
            for name in fields
        }

        if all(value is not None for _, value in values.items()):
            spec = settings.get('GECOS', "{givenName} {sn}")
            d['gecos'] = spec.format(**values)

    if 'primary_group' in changes:
        group = get_value(changes, 'primary_group')
        assert group['gidNumber'] is not None
        d['gidNumber'] = group['gidNumber']

    changes = changes.merge(d)
    return changes


# SHADOW

def get_fields_shadow() -> List[tldap.fields.Field]:
    fields = [
        tldap.fields.DaysSinceEpochField('shadowLastChange')
    ]
    return fields


def load_shadow(python_data: LdapObject) -> LdapObject:
    return python_data


def save_shadow(changes: Changeset) -> Changeset:
    if 'password' in changes:
        changes = changes.merge({
            'shadowLastChange': datetime.datetime.now().date()
        })
    return changes


# GROUP

def get_fields_group() -> List[tldap.fields.Field]:
    fields = [
        tldap.fields.CharField('cn'),
        tldap.fields.CharField('description'),
        tldap.fields.IntegerField('gidNumber'),
        tldap.fields.CharField('memberUid', max_instances=None),
        tldap.fields.FakeField('members'),
    ]
    return fields


def load_group(python_data: LdapObject, account_table: LdapObjectClass) -> LdapObject:
    d = {}

    if 'gidNumber' in python_data:
        d['members'] = NotLoadedListToList(table=account_table, key='uid', value=python_data['memberUid'])

    return python_data.merge(d)


def save_group(changes: Changeset) -> Changeset:
    d = {}

    changes = changes.merge(d)

    d = {}

    if 'cn' in changes:
        cn = get_value(changes, 'cn')
        description = get_value(changes, 'description')
        if description is None:
            d['description'] = cn

    if 'members' in changes:
        members = get_value(changes, 'members')
        d['memberUid'] = [v['uid'] for v in members]

    return changes.merge(d)


def add_group_member(changes: Changeset, member: LdapObject) -> Changeset:
    add_uid = member['uid']
    member_uid = get_value(changes, 'memberUid')
    if add_uid not in member_uid:
        # Do not use: member_uid += [add_uid]
        # It will mutate member_uid.
        member_uid = member_uid + [add_uid]
    changes = changes.merge({
        'memberUid': member_uid
    })
    return changes


def remove_group_member(changes: Changeset, member: LdapObject) -> Changeset:
    rm_uid = member['uid']
    member_uid = get_value(changes, 'memberUid')
    changes = changes.merge({
        'memberUid': [uid for uid in member_uid if uid != rm_uid]
    })
    return changes


# PWDPOLICY

def get_fields_pwdpolicy() -> List[tldap.fields.Field]:
    fields = [
        tldap.fields.CharField('pwdAttribute'),
        tldap.fields.CharField('pwdAccountLockedTime'),
    ]
    return fields


def load_pwdpolicy(python_data: LdapObject) -> LdapObject:
    python_data = python_data.merge({
        'locked': python_data['pwdAccountLockedTime'] is not None,
    })
    return python_data


def save_pwdpolicy(changes: Changeset) -> Changeset:
    d = {}

    if get_value(changes, 'locked') is None:
        d['locked'] = False

    changes = changes.merge(d)

    d = {}

    pwd_attribute = get_value(changes, 'pwdAttribute')
    if pwd_attribute is None:
        d['pwdAttribute'] = 'userPassword'

    if 'locked' in changes:
        locked = get_value(changes, 'locked')
        if locked:
            d['pwdAccountLockedTime'] = '000001010000Z'
        else:
            d['pwdAccountLockedTime'] = None

    changes = changes.merge(d)
    return changes


# PASSWORD_OBJECT - ds389

def get_fields_password_object() -> List[tldap.fields.Field]:
    fields = [
        tldap.fields.CharField('nsAccountLock'),
    ]
    return fields


def load_password_object(python_data: LdapObject) -> LdapObject:
    def is_locked():
        account_lock = python_data['nsAccountLock']
        if account_lock is None:
            return False
        else:
            return account_lock.lower() == 'true'

    python_data = python_data.merge({
        'locked': is_locked()
    })
    return python_data


def save_password_object(changes: Changeset) -> Changeset:
    d = {}

    if get_value(changes, 'locked') is None:
        d['locked'] = False

    changes = changes.merge(d)

    d = {}

    if 'locked' in changes:
        locked = get_value(changes, 'locked')
        if locked:
            d['nsAccountLock'] = "TRUE"
        else:
            d['nsAccountLock'] = None

    changes = changes.merge(d)
    return changes


# SHIBBOLETH

def get_fields_shibboleth() -> List[tldap.fields.Field]:
    fields = [
        tldap.fields.CharField('auEduPersonSharedToken'),
        tldap.fields.CharField('eduPersonAffiliation'),
    ]
    return fields


def load_shibboleth(python_data: LdapObject) -> LdapObject:
    return python_data


def save_shibboleth(changes: Changeset, database: Database) -> Changeset:
    d = {}
    settings = database.settings

    if 'uid' in changes:
        uid = get_value(changes, 'uid')
        token = get_value(changes, 'auEduPersonSharedToken')
        if token is None:
            entity_id = settings['SHIBBOLETH_URL']
            salt = settings['SHIBBOLETH_SALT']
            token = base64.urlsafe_b64encode(sha1(uid + entity_id + salt).digest())[:-1]
            d['auEduPersonSharedToken'] = token

    if 'locked' in changes:
        locked = get_value(changes, 'locked')
        if locked:
            d['eduPersonAffiliation'] = 'affiliate'
        else:
            d['eduPersonAffiliation'] = 'staff'

    changes = changes.merge(d)
    return changes
