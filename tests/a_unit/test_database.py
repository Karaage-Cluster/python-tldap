#!/usr/bin/env python
# -*- coding: UTF-8 -*-

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
import datetime
import os
from typing import Optional, List

import mock
import pytest

import tldap
import tldap.database
import tldap.database.helpers
import tldap.transaction
import tldap.exceptions
import tldap.modlist
import tldap.test.slapd
import tests.database
from tldap import Q
import tldap.query


class SearchMock:
    def __init__(self):
        self.calls = []
        self.results = []

    def add_result(self, search: bytes, obj: tldap.database.LdapObject):
        assert isinstance(search, bytes)
        self.results.append((b"(%s)" % search, obj))

    def __call__(
            self, base: str, scope: str, filterstr: bytes=b'(objectClass=*)',
            attrlist: Optional[List[str]]=None, limit: Optional[int]=None):

        self.calls.append((base, scope, filterstr, attrlist, limit))

        results = []
        for search, obj in self.results:
            if search in filterstr:
                obj_values = obj.to_dict()
                results.append(
                    (obj['dn'], get_db_values(obj_values, type(obj)))
                )
        return results

    def reset(self):
        self.calls = []


class Defaults:
    pass


@pytest.fixture
def group1(mock_ldap):
    """ Get group 1. """
    group = tests.database.Group()
    group = group.merge({
        'cn': 'group1',
        'gidNumber': 10,
        'memberUid': [],
    })
    group = tldap.database.insert(group)
    mock_ldap.reset_mock()
    return group


@pytest.fixture
def defaults(group1):
    """ Get globals for all model tests. """

    values = Defaults()
    values.account_attributes = {
        'uid': "tux",
        'uidNumber': 10,
        'givenName': "Tux",
        'sn': "Torvalds",
        'cn': "Tux Torvalds",
        'telephoneNumber': "000",
        'mail': "tuz@example.org",
        'o': "Linux Rules",
        'password': "silly",
        'homeDirectory': "/home/tux",
        'loginShell': "/bin/bash",
        'primary_group': group1,
    }

    return values


@pytest.fixture
def account1(defaults, mock_ldap):
    """ Get an account. """
    # old_search = mock_ldap.search
    # mock_ldap.search = mock.MagicMock(return_value=[])

    account = tests.database.Account()
    account = account.merge(defaults.account_attributes)
    account = tldap.database.insert(account)

    # mock_ldap.search = old_search
    mock_ldap.reset_mock()
    return account


@pytest.fixture
def group2(account1, mock_ldap):
    """ Get group 2. """
    group = tests.database.Group()
    group = group.merge({
        'cn': 'group2',
        'gidNumber': 11,
        'members': [account1],
    })
    group = tldap.database.insert(group)
    mock_ldap.reset_mock()
    return group


class TestObject:
    def __ne__(self, other):
        return not self.__eq__(other)


class UnorderedList(TestObject):
    """ A helper object that compares two unordered lists."""

    def __init__(self, l):
        self._l = l

    def __eq__(self, other):
        t = list(self._l)   # make a mutable copy
        try:
            for elem in other:
                t.remove(elem)
        except ValueError:
            return False
        return not t

    def __repr__(self):
        return '<unordered_list %s>' % self._l


class CheckInstance(TestObject):

    def __init__(self, instance_type):
        self._type = instance_type

    def __eq__(self, other):
        return isinstance(other, self._type)

    def __repr__(self):
        return '<type %s>' % self._type


def _get_db_value(value):
    """ Convert value into db value. """
    if isinstance(value, str):
        result = value.encode("UTF-8")
    elif isinstance(value, int):
        result = b"%d" % value
    elif isinstance(value, bytes):
        result = value
    else:
        assert False

    return result


def get_python_expected_values(updates):
    result = {}

    for key, value in updates.items():
        if key == "password":
            result['password'] = []
            result['userPassword'] = [mock.ANY]
        elif key == "primary_group":
            result[key] = [CheckInstance(tldap.database.NotLoadedObject)]
        elif value is None:
            result[key] = []
        else:
            result[key] = [value]

    return result


def get_db_values(updates, table: tldap.database.LdapObjectClass):
    """ Convert values into something we can compare against db values. """
    result = {}

    for key, value in updates.items():
        field = table.get_fields()[key]

        if isinstance(value, list) and not field.is_list:
            if len(value) == 1:
                value = value[0]
            elif len(value) == 0:
                value = None
            else:
                assert False, value

        if key == "dn":
            pass
        elif key == "password":
            pass
        elif key == "locked":
            pass
        elif key == "groups":
            pass
        elif key == "primary_group":
            if not isinstance(value, tldap.database.NotLoadedObject):
                if value is None:
                    result["gidNumber"] = []
                else:
                    result["gidNumber"] = [str(value.get_as_single('gidNumber')).encode("UTF-8")]
        elif value is None:
            result[key] = []
        elif value is mock.ANY:
            result[key] = [value]
        elif isinstance(value, TestObject):
            result[key] = [value]
        elif key == "shadowLastChange":
            value = value - datetime.date(year=1970, month=1, day=1)
            result[key] = [str(value.days).encode("UTF-8")]
        elif key == "members":
            if not any(isinstance(v, tldap.database.NotLoadedObject) for v in value):
                result['memberUid'] = [v.get_as_single('uid') for v in value]
        elif key == "groups":
            pass
        elif isinstance(value, list):
            value = [
                _get_db_value(v)
                for v in value
            ]
            result[key] = value
        elif isinstance(value, int):
            result[key] = [str(value).encode("UTF-8")]
        else:
            result[key] = [value.encode("UTF-8")]

    if issubclass(table, tests.database.Account):
        if os.environ['LDAP_TYPE'] == 'openldap':
            result['objectClass'] = [
                b'top', b'person', b'inetOrgPerson', b'organizationalPerson',
                b'shadowAccount', b'posixAccount', b'pwdPolicy',
            ]
            result['pwdAttribute'] = [b'userPassword']
        elif os.environ['LDAP_TYPE'] == 'ds389':
            result['objectClass'] = [
                b'top', b'person', b'inetOrgPerson', b'organizationalPerson',
                b'shadowAccount', b'posixAccount', b'passwordObject',
            ]

    return result


def get_db_expected_values(updates, table: tldap.database.LdapObjectClass):
    """ Convert values into something we can compare against db values. """
    result = {}

    updates = get_db_values(updates, table)

    for key, value in updates.items():
        result[key] = UnorderedList(value)

    return result


class TestModelAccount:
    def test_create(self, defaults, mock_ldap):
        """ Test create LDAP object. """
        c = mock_ldap
        account_attributes = defaults.account_attributes

        # Create the object.
        account = tests.database.Account()
        account = account.merge(account_attributes)
        account = tldap.database.insert(account)

        # Simulate required attributes that should be added.
        expected_values = dict(account_attributes)
        expected_values.update({
            'gecos': "Tux Torvalds",
            'displayName': "Tux Torvalds",
            'shadowLastChange': mock.ANY,
            'userPassword': mock.ANY,
            'dn': "uid=tux,ou=People,dc=python-ldap,dc=org",
        })
        python_expected_values = get_python_expected_values(expected_values)
        db_expected_values = get_db_expected_values(expected_values, tests.database.Account)

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.add(
                'uid=tux,ou=People,dc=python-ldap,dc=org',
                db_expected_values,
            )
        ]
        c.assert_has_calls(expected_calls)

        # Assert caches are correct.
        for key, value in python_expected_values.items():
            assert account[key] == value, key

    def test_create_with_dn(self, defaults, mock_ldap):
        """ Test create LDAP object. """
        c = mock_ldap
        account_attributes = defaults.account_attributes

        # Create the object.
        account = tests.database.Account()
        account = account.merge(account_attributes)
        account = account.merge({'dn': "uid=penguin,ou=People,dc=python-ldap,dc=org"})
        account = tldap.database.insert(account)

        # Simulate required attributes that should be added.
        expected_values = dict(account_attributes)
        expected_values.update({
            'gecos': "Tux Torvalds",
            'displayName': "Tux Torvalds",
            'shadowLastChange': mock.ANY,
            'userPassword': mock.ANY,
            'dn': "uid=penguin,ou=People,dc=python-ldap,dc=org",
        })
        python_expected_values = get_python_expected_values(expected_values)
        db_expected_values = get_db_expected_values(expected_values, tests.database.Account)

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.add(
                'uid=penguin,ou=People,dc=python-ldap,dc=org',
                db_expected_values,
            )
        ]
        c.assert_has_calls(expected_calls)

        # Assert caches are correct.
        for key, value in python_expected_values.items():
            assert account[key] == value, key

    def test_search(self, defaults, mock_ldap, account1, group1):
        """ Test delete LDAP object. """
        c = mock_ldap
        c.search = SearchMock()
        account1 = account1.merge({
            'primary_group': group1,
        })
        c.search.add_result(b"uid=tux", account1)

        results = tldap.database.search(tests.database.Account, Q(uid='does_not_exist'))
        assert list(results) == []

        results = tldap.database.search(tests.database.Account, Q(uid='tux'))
        results = list(results)
        assert len(results) == 1

        account = results[0]

        account_attributes = defaults.account_attributes
        expected_values = dict(account_attributes)
        expected_values.update({
            'gecos': "Tux Torvalds",
            'displayName': "Tux Torvalds",
            'shadowLastChange': mock.ANY,
            'userPassword': mock.ANY,
            'dn': "uid=tux,ou=People,dc=python-ldap,dc=org",
        })
        python_expected_values = get_python_expected_values(expected_values)

        # Assert caches are correct.
        for key, value in python_expected_values.items():
            assert account[key] == value, key

    def test_search_by_dn(self, mock_ldap, account1):
        """ Test getting a person. """
        c = mock_ldap
        c.search = SearchMock()

        c.search.add_result(
            b"entryDN:=uid=tux, ou=People, dc=python-ldap,dc=org", account1)

        person = tldap.database.get_one(
            tests.database.Account,
            Q(dn="uid=tux, ou=People, dc=python-ldap,dc=org"))
        assert person.get_as_single('uid') == "tux"

        expected_calls = [(
            'ou=People, dc=python-ldap,dc=org',
            'SUBTREE',
            b'(&'
            b'(objectClass=inetOrgPerson)'
            b'(objectClass=organizationalPerson)'
            b'(objectClass=person)'
            b'(entryDN:=uid=tux, ou=People, dc=python-ldap,dc=org)'
            b')',
            mock.ANY,
            None
        )]
        assert c.search.calls == expected_calls

    def test_delete(self, mock_ldap, account1):
        """ Test delete LDAP object. """
        c = mock_ldap

        # Delete the object.
        tldap.database.delete(account1)

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.delete(
                'uid=tux,ou=People,dc=python-ldap,dc=org',
            )
        ]
        c.assert_has_calls(expected_calls)

    def test_rename(self, defaults, mock_ldap, account1):
        """ Test rename LDAP object. """
        c = mock_ldap

        # Rename the object.
        account1 = tldap.database.rename(account1, uid='tuz')

        # Simulate required attributes that should be added.
        expected_values = dict(defaults.account_attributes)
        expected_values.update({
            'uid': "tuz",
        })
        python_expected_values = get_python_expected_values(expected_values)

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.rename(
                'uid=tux,ou=People,dc=python-ldap,dc=org',
                'uid=tuz',
                None,
            )
        ]
        c.assert_has_calls(expected_calls)

        # Assert caches are correct.
        assert account1.get_as_single('dn') == "uid=tuz,ou=People,dc=python-ldap,dc=org"
        for key, value in python_expected_values.items():
            assert account1[key] == value, key

    def test_move(self, defaults, mock_ldap, account1):
        """ Test move LDAP object. """
        c = mock_ldap

        # Move the object.
        account1 = tldap.database.rename(account1, "ou=Groups, dc=python-ldap,dc=org")

        # Simulate required attributes that should be added.
        expected_values = dict(defaults.account_attributes)
        python_expected_values = get_python_expected_values(expected_values)

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.rename(
                'uid=tux,ou=People,dc=python-ldap,dc=org',
                'uid=tux',
                'ou=Groups, dc=python-ldap,dc=org',
            )
        ]
        c.assert_has_calls(expected_calls)

        # Assert caches are correct.
        assert account1.get_as_single('dn') == "uid=tux,ou=Groups,dc=python-ldap,dc=org"
        for key, value in python_expected_values.items():
            assert account1[key] == value, key

    def test_add_attribute(self, defaults, mock_ldap, account1):
        """ Test add new attribute. """
        c = mock_ldap

        # Replace the attribute.
        changes = tldap.database.changeset(account1, {'title': "Superior"})
        account1 = tldap.database.save(changes)

        # Simulate required attributes that should be added.
        expected_values = dict(defaults.account_attributes)
        expected_values.update({
            'title': "Superior"
        })
        python_expected_values = get_python_expected_values(expected_values)

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.modify(
                'uid=tux,ou=People,dc=python-ldap,dc=org',
                {'title': [('MODIFY_REPLACE', [b'Superior'])]},
            )
        ]
        c.assert_has_calls(expected_calls)

        # Assert caches are correct.
        assert account1.get_as_single('dn') == "uid=tux,ou=People,dc=python-ldap,dc=org"
        for key, value in python_expected_values.items():
            assert account1[key] == value, key

    def test_replace_dn(self, account1):
        """ Test replace LDAP attribute. """
        # Replace the attribute.
        changes = tldap.database.changeset(account1, {'dn': "uid=penguin,ou=People,dc=python-ldap,dc=org"})
        with pytest.raises(RuntimeError):
            tldap.database.save(changes)

    def test_replace_attribute(self, defaults, mock_ldap, account1):
        """ Test replace LDAP attribute. """
        c = mock_ldap

        # Replace the attribute.
        changes = tldap.database.changeset(account1, {'sn': "Closed"})
        changes = changes.merge({'sn': "Gates", 'cn': "Tux Gates"})
        account1 = tldap.database.save(changes)

        # Simulate required attributes that should be added.
        expected_values = dict(defaults.account_attributes)
        expected_values.update({
            'cn': 'Tux Gates',
            'displayName': 'Tux Gates',
            'gecos': 'Tux Gates',
            'sn': "Gates",
        })
        python_expected_values = get_python_expected_values(expected_values)

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.modify(
                'uid=tux,ou=People,dc=python-ldap,dc=org',
                {
                    'cn': [('MODIFY_REPLACE', [b'Tux Gates'])],
                    'displayName': [('MODIFY_REPLACE', [b'Tux Gates'])],
                    'gecos': [('MODIFY_REPLACE', [b'Tux Gates'])],
                    'sn': [('MODIFY_REPLACE', [b'Gates'])],
                },
            )
        ]
        c.assert_has_calls(expected_calls)

        # Assert caches are correct.
        assert account1.get_as_single('dn') == "uid=tux,ou=People,dc=python-ldap,dc=org"
        for key, value in python_expected_values.items():
            assert account1[key] == value, key

    def test_replace_attribute_same(self, account1):
        """ Test replace LDAP attribute. """

        # Replace the attribute.
        changes = tldap.database.changeset(account1, {'sn': "Torvalds"})
        assert 'sn' not in changes

        # Replace the attribute.
        changes = tldap.database.changeset(account1, {})
        changes = changes.set('sn', "Torvalds")
        assert 'sn' not in changes

        # Replace the attribute.
        changes = tldap.database.changeset(account1, {})
        changes = changes.merge({'sn': "Torvalds"})
        assert 'sn' not in changes

    def test_replace_attribute_error(self, account1):
        """ Test replace LDAP attribute with invalid value. """

        # Replace the attribute.
        changes = tldap.database.changeset(account1, {'gidNumber': "Torvalds"})

        assert not changes.is_valid
        assert changes.errors == ["gidNumber: should be a integer."]

        with pytest.raises(RuntimeError):
            tldap.database.save(changes)

    def test_delete_attribute(self, defaults, mock_ldap, account1):
        """ Test delete LDAP attribute. """
        """ Test replace LDAP attribute. """
        c = mock_ldap

        # Replace the attribute.
        changes = tldap.database.changeset(account1, {'telephoneNumber': None})
        account1 = tldap.database.save(changes)

        # Simulate required attributes that should be added.
        expected_values = dict(defaults.account_attributes)
        expected_values.update({
            'telephoneNumber': None,
        })
        python_expected_values = get_python_expected_values(expected_values)

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.modify(
                'uid=tux,ou=People,dc=python-ldap,dc=org',
                {
                    'telephoneNumber': [('MODIFY_DELETE', [])],
                },
            )
        ]
        c.assert_has_calls(expected_calls)

        # Assert caches are correct.
        assert account1.get_as_single('dn') == "uid=tux,ou=People,dc=python-ldap,dc=org"
        for key, value in python_expected_values.items():
            assert account1[key] == value, key


class TestModelGroup:
    def test_set_primary_group(
            self, mock_ldap, account1, group2):
        """ Test setting primary group for account. """
        c = mock_ldap

        # Add person to group.
        changes = tldap.database.changeset(account1, {'primary_group': group2})
        tldap.database.save(changes)

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.modify(
                'uid=tux,ou=People,dc=python-ldap,dc=org',
                {'gidNumber': [('MODIFY_REPLACE', [b'11'])]},
            )
        ]
        c.assert_has_calls(expected_calls)

    def test_get_primary_group(
            self, mock_ldap, account1, group1):
        """ Test getting primary group for account. """

        c = mock_ldap
        c.search = SearchMock()
        c.search.add_result(b"gidNumber=10", group1)

        # Get the primary group
        account1 = tldap.database.preload(account1)
        group = account1.get_as_single('primary_group')

        for key in ["cn", "description", "gidNumber", "memberUid"]:
            assert group[key] == group1[key]

    def test_add_secondary_group(
            self, mock_ldap, account1, group1):
        """ Test adding existing secondary group to account. """
        c = mock_ldap
        c.search = SearchMock()

        # Add person to group.
        changes = tldap.database.changeset(group1, {})
        changes = tests.database.Group.add_member(changes, account1)
        tldap.database.save(changes)

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.modify(
                'cn=group1,ou=Group,dc=python-ldap,dc=org',
                {'memberUid': [('MODIFY_ADD', [b'tux'])]},
            )
        ]
        c.assert_has_calls(expected_calls)

    def test_remove_secondary_group(
            self, mock_ldap, account1, group2):
        """ Test removing secondary group from account. """
        c = mock_ldap
        c.search = SearchMock()

        # Add person to group.
        changes = tldap.database.changeset(group2, {})
        changes = tests.database.Group.remove_member(changes, account1)
        tldap.database.save(changes)

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.modify(
                'cn=group2,ou=Group,dc=python-ldap,dc=org',
                {'memberUid': [('MODIFY_DELETE', [b'tux'])]},
            )
        ]
        c.assert_has_calls(expected_calls)

    def test_get_secondary_group_none(
            self, mock_ldap, account1):
        """ Test getting secondary group when none set. """
        c = mock_ldap
        c.search = SearchMock()

        # Don't try to preload primary group, it will fail.
        account1 = account1.set('primary_group', None)

        # Get the secondary groups.
        account1 = tldap.database.preload(account1)

        # Test result
        groups = account1['groups']
        assert groups == []

    def test_get_secondary_group_set(
            self, mock_ldap, account1, group2):
        """ Test getting secondary group when one set. """
        c = mock_ldap
        c.search = SearchMock()
        c.search.add_result(b"memberUid=tux", group2)

        # Don't try to preload primary group, it will fail.
        account1 = account1.set('primary_group', None)

        # Get the secondary groups.
        account1 = tldap.database.preload(account1)

        # Test result
        groups = account1['groups']
        assert len(groups) == 1

        group = groups[0]
        for key in ["cn", "description", "gidNumber"]:
            assert group[key] == group2[key], key
