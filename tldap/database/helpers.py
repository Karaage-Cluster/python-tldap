import base64
import datetime
from hashlib import sha1
from typing import Iterator, List, Set

import tldap.exceptions
import tldap.fields
from tldap.database import LdapObject, LdapChanges, NotLoadedObject, NotLoadedList, \
    NotLoadedListToList, LdapObjectClass
from tldap.dn import str2dn, dn2str
import tldap.ldap_passwd as ldap_passwd


def rdn_to_dn(changes: LdapChanges, name: str, base_dn: str) -> LdapChanges:
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


def set_object_class(changes: LdapChanges, object_class: List[str]) -> LdapChanges:
    if get_value(changes, 'objectClass') is None:
        changes = changes.set('objectClass', object_class)
    return changes


def get_value(changes: LdapChanges, key: str) -> any:
    if key.startswith("_"):
        raise RuntimeError("This function should not be used for private values.")
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


def save_person(changes: LdapChanges) -> LdapChanges:
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


def save_account(changes: LdapChanges) -> LdapChanges:
    d = {}

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
            if home_directory is None:
                d['homeDirectory'] = '/home/%s' % uid

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

    if 'givenName' in changes or 'sn' in changes:
        given_name = get_value(changes, 'givenName')
        sn = get_value(changes, 'sn')

        if given_name is not None and sn is not None:
            d['gecos'] = '%s %s' % (given_name, sn)

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


def save_shadow(changes: LdapChanges) -> LdapChanges:
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


def save_group(changes: LdapChanges) -> LdapChanges:
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


def save_pwdpolicy(changes: LdapChanges) -> LdapChanges:
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


# SHIBBOLETH

def get_fields_shibboleth() -> List[tldap.fields.Field]:
    fields = [
        tldap.fields.CharField('auEduPersonSharedToken'),
        tldap.fields.CharField('eduPersonAffiliation'),
    ]
    return fields


def load_shibboleth(python_data: LdapObject) -> LdapObject:
    return python_data


def save_shibboleth(changes: LdapChanges, settings: dict) -> LdapChanges:
    d = {}

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
