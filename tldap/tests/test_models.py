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

import mock
import pytest

import tldap
import tldap.schemas.rfc
import tldap.transaction
import tldap.exceptions
import tldap.modlist

import tldap.test.slapd
import tldap.tests.schemas as test_schemas


class SearchMock():
    def __init__(self):
        self.results = []

    def add_result(self, search, obj):
        self.results.append(("(%s)" % search, obj))

    def __call__(
            self, base, scope, filterstr='(objectClass=*)',
            attrlist=None, limit=None):

        results = []
        for search, obj in self.results:
            if search in filterstr:
                results.append(
                    (obj._dn, get_db_values(obj._db_values))
                )
        return results


class Defaults:
    pass


@pytest.fixture
def defaults():
    """ Get globals for all model tests. """

    values = Defaults()
    values.person = test_schemas.person
    values.DoesNotExist = values.person.DoesNotExist
    values.AlreadyExists = values.person.AlreadyExists
    values.get = values.person.objects.get
    values.get_or_create = values.person.objects.get_or_create
    values.all_person_attributes = {
        'st', 'labeledURI', 'userPKCS12', 'postOfficeBox', 'l',
        'internationaliSDNNumber', 'manager', 'mobile', 'objectClass',
        'physicalDeliveryOfficeName', 'preferredDeliveryMethod', 'postalCode',
        'departmentNumber', 'ou', 'homePhone', 'userPassword',
        'teletexTerminalIdentifier', 'givenName', 'x121Address',
        'x500uniqueIdentifier', 'jpegPhoto', 'employeeNumber', 'cn',
        'preferredLanguage', 'carLicense', 'uid', 'seeAlso', 'audio',
        'homePostalAddress', 'mail', 'description', 'destinationIndicator',
        'sn', 'roomNumber', 'businessCategory', 'userSMIMECertificate',
        'userCertificate', 'street', 'pager', 'employeeType', 'initials',
        'secretary', 'telexNumber', 'o', 'photo', 'facsimileTelephoneNumber',
        'title', 'displayName', 'postalAddress', 'telephoneNumber'}

    values.account = test_schemas.account
    values.group = test_schemas.group

    values.person_attributes = {
        'uid': "tux",
        'givenName': "Tux",
        'sn': "Torvalds",
        'cn': "Tux Torvalds",
        'telephoneNumber': "000",
        'mail': "tuz@example.org",
        'o': "Linux Rules",
        'userPassword': "silly",
    }

    values.account_attributes = {
        'uid': "tux",
        'gidNumber': 0,
        'givenName': "Tux",
        'sn': "Torvalds",
        'cn': "Tux Torvalds",
        'telephoneNumber': "000",
        'mail': "tuz@example.org",
        'o': "Linux Rules",
        'userPassword': "silly",
        'homeDirectory': "/home/tux",
    }

    return values


@pytest.fixture
def person(defaults, mock_LDAP):
    """ Get a person. """
    person = defaults.person.objects.create(**defaults.person_attributes)
    mock_LDAP.reset_mock()
    return person


@pytest.fixture
def account1(defaults, mock_LDAP):
    """ Get an account. """
    old_search = mock_LDAP.search
    mock_LDAP.search = mock.MagicMock(return_value=[])

    account = defaults.account.objects.create(**defaults.account_attributes)

    mock_LDAP.search = old_search
    mock_LDAP.reset_mock()
    return account


@pytest.fixture
def group1(defaults, mock_LDAP):
    """ Get group 1. """
    group = defaults.group.objects.create(
        cn="group1", gidNumber=10, memberUid=[])
    mock_LDAP.reset_mock()
    return group


@pytest.fixture
def group2(defaults, person, mock_LDAP):
    """ Get group 2. """
    group = defaults.group.objects.create(
        cn="group2", gidNumber=11, memberUid=[person.uid])
    mock_LDAP.reset_mock()
    return group


class unordered_list(object):
    "A helper object that compares two unordered lists."

    def __init__(self, l):
        self.l = l

    def __eq__(self, other):
        t = list(self.l)   # make a mutable copy
        try:
            for elem in other:
                t.remove(elem)
        except ValueError:
            return False
        return not t

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return '<unordered_list %s>' % self.l


def get_expected_initial_db_values():
    """ Get initial db values for new person. """
    return {
        'audio': [],
        'businessCategory': [],
        'carLicense': [],
        'cn': [],
        'departmentNumber': [],
        'description': [],
        'destinationIndicator': [],
        'displayName': [],
        'employeeNumber': [],
        'employeeType': [],
        'facsimileTelephoneNumber': [],
        'givenName': [],
        'homePhone': [],
        'homePostalAddress': [],
        'initials': [],
        'internationaliSDNNumber': [],
        'jpegPhoto': [],
        'l': [],
        'labeledURI': [],
        'mail': [],
        'manager': [],
        'mobile': [],
        'o': [],
        'objectClass': [],
        'ou': [],
        'pager': [],
        'photo': [],
        'physicalDeliveryOfficeName': [],
        'postOfficeBox': [],
        'postalAddress': [],
        'postalCode': [],
        'preferredDeliveryMethod': [],
        'preferredLanguage': [],
        'roomNumber': [],
        'secretary': [],
        'seeAlso': [],
        'sn': [],
        'st': [],
        'street': [],
        'telephoneNumber': [],
        'teletexTerminalIdentifier': [],
        'telexNumber': [],
        'title': [],
        'uid': [],
        'userCertificate': [],
        'userPKCS12': [],
        'userPassword': [],
        'userSMIMECertificate': [],
        'x121Address': [],
        'x500uniqueIdentifier': [],
    }


def get_db_values(updates):
    """ Convert values into db values. """
    result = {}

    for key, value in updates.items():
        if isinstance(value, list):
            result[key] = value
        else:
            result[key] = [value.encode("UTF-8")]

    return result


def get_expected_values(updates):
    """ Convert values into something we can compare against db values. """
    result = {}

    for key, value in updates.items():
        if isinstance(value, list):
            result[key] = unordered_list(value)
        elif isinstance(value, int):
            result[key] = unordered_list([str(value).encode("UTF-8")])
        else:
            result[key] = unordered_list([value.encode("UTF-8")])

    return result


def update_expected_db_values(db_values, updates):
    """ Update db values with updates. """
    result = dict(db_values)

    for key, value in updates.items():
        if value is None:
            result[key] = []
        elif isinstance(value, list):
            result[key] = unordered_list(value)
        else:
            result[key] = unordered_list([value.encode("UTF-8")])

    return result


def get_testable_values(values):
    """ Convert db values into something we can use for testing. """
    result = {}

    for key, value in values.items():
        assert isinstance(value, list)
        result[key] = unordered_list(value)

    return result


class TestModelPerson:
    def test_create(self, defaults, mock_LDAP):
        """ Test create LDAP object. """
        c = mock_LDAP
        person_attributes = dict(defaults.person_attributes)
        expected_db_values = get_expected_initial_db_values()

        # Create the object.
        person = defaults.person.objects.create(**person_attributes)

        # Simulate required attributes that should be added.
        person_attributes.update({
            'objectClass':
                [b'person', b'top', b'inetOrgPerson', b'organizationalPerson']
        })

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.add(
                'uid=tux,ou=People,dc=python-ldap,dc=org',
                get_expected_values(person_attributes),
                mock.ANY,
            )
        ]
        c.assert_has_calls(expected_calls)

        # Assert caches are correct.
        assert person._alias == "default"
        assert person._dn == "uid=tux,ou=People,dc=python-ldap,dc=org"
        assert person._db_values == update_expected_db_values(
            expected_db_values, person_attributes)

        # Simulate failure.
        args, kwargs = c.add.call_args
        onfailure = args[2]
        onfailure()

        # Assert caches are correct.
        assert person._alias is None
        assert person._dn == "uid=tux,ou=People,dc=python-ldap,dc=org"
        assert person._db_values is None

    def test_delete(self, defaults, mock_LDAP, person):
        """ Test delete LDAP object. """
        c = mock_LDAP
        expected_db_values = get_testable_values(person._db_values)

        # Delete the object.
        person.delete()

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.delete(
                'uid=tux,ou=People,dc=python-ldap,dc=org',
                mock.ANY,
            )
        ]
        c.assert_has_calls(expected_calls)

        # Assert caches are correct.
        assert person._alias == "default"
        assert person._dn == "uid=tux,ou=People,dc=python-ldap,dc=org"
        assert person._db_values is None

        # Simulate failure.
        args, kwargs = c.delete.call_args
        onfailure = args[1]
        onfailure()

        # Assert caches are correct.
        assert person._alias == "default"
        assert person._dn == "uid=tux,ou=People,dc=python-ldap,dc=org"
        assert person._db_values == expected_db_values

    def test_rename(self, defaults, mock_LDAP, person):
        """ Test rename LDAP object. """
        c = mock_LDAP
        expected_db_values = get_testable_values(person._db_values)

        # Rename the object.
        person.rename(uid='tuz')

        # Simulate required attributes that should be added.
        person_attributes = {'uid': "tuz"}

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.rename(
                'uid=tux,ou=People,dc=python-ldap,dc=org',
                'uid=tuz',
                None,
                mock.ANY,
            )
        ]
        c.assert_has_calls(expected_calls)

        # Assert caches are correct.
        assert person._alias == "default"
        assert person._dn == "uid=tuz,ou=People,dc=python-ldap,dc=org"
        assert person._db_values == update_expected_db_values(
            expected_db_values, person_attributes)

        # Simulate failure.
        args, kwargs = c.rename.call_args
        onfailure = args[3]
        onfailure()

        # Assert caches are correct.
        assert person._alias == "default"
        assert person._dn == "uid=tux,ou=People,dc=python-ldap,dc=org"
        assert person._db_values == expected_db_values

    def test_move(self, defaults, mock_LDAP, person):
        """ Test move LDAP object. """
        c = mock_LDAP
        expected_db_values = get_testable_values(person._db_values)

        # Move the object.
        person.rename("ou=Groups, dc=python-ldap,dc=org")

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.rename(
                'uid=tux,ou=People,dc=python-ldap,dc=org',
                'uid=tux',
                'ou=Groups, dc=python-ldap,dc=org',
                mock.ANY,
            )
        ]
        c.assert_has_calls(expected_calls)

        # Assert caches are correct.
        assert person._alias == "default"
        assert person._dn == "uid=tux,ou=Groups,dc=python-ldap,dc=org"
        assert person._db_values == expected_db_values

        # Simulate failure.
        args, kwargs = c.rename.call_args
        onfailure = args[3]
        onfailure()

        # Assert caches are correct.
        assert person._alias == "default"
        assert person._dn == "uid=tux,ou=People,dc=python-ldap,dc=org"
        assert person._db_values == expected_db_values

    def test_add_attribute(self, defaults, mock_LDAP, person):
        """ Test add new attribute. """
        c = mock_LDAP
        expected_db_values = get_testable_values(person._db_values)

        # Replace the attribute.
        person.title = "Superior"
        person.save()

        # Simulate required attributes that should be added.
        person_attributes = {'title': "Superior"}

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.modify(
                'uid=tux,ou=People,dc=python-ldap,dc=org',
                {'title': ('MODIFY_ADD', [b'Superior'])},
                mock.ANY,
            )
        ]
        c.assert_has_calls(expected_calls)

        # Assert caches are correct.
        assert person._alias == "default"
        assert person._dn == "uid=tux,ou=People,dc=python-ldap,dc=org"
        assert person._db_values == update_expected_db_values(
            expected_db_values, person_attributes)

        # Simulate failure.
        args, kwargs = c.modify.call_args
        onfailure = args[2]
        onfailure()

        # Assert caches are correct.
        assert person._alias == "default"
        assert person._dn == "uid=tux,ou=People,dc=python-ldap,dc=org"
        assert person._db_values == expected_db_values

    def test_replace_attribute(self, defaults, mock_LDAP, person):
        """ Test replace LDAP attribute. """
        c = mock_LDAP
        expected_db_values = get_testable_values(person._db_values)

        # Replace the attribute.
        person.sn = "Gates"
        person.save()

        # Simulate required attributes that should be added.
        person_attributes = {'sn': "Gates"}

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.modify(
                'uid=tux,ou=People,dc=python-ldap,dc=org',
                {'sn': ('MODIFY_REPLACE', [b'Gates'])},
                mock.ANY,
            )
        ]
        c.assert_has_calls(expected_calls)

        # Assert caches are correct.
        assert person._alias == "default"
        assert person._dn == "uid=tux,ou=People,dc=python-ldap,dc=org"
        assert person._db_values == update_expected_db_values(
            expected_db_values, person_attributes)

        # Simulate failure.
        args, kwargs = c.modify.call_args
        onfailure = args[2]
        onfailure()

        # Assert caches are correct.
        assert person._alias == "default"
        assert person._dn == "uid=tux,ou=People,dc=python-ldap,dc=org"
        assert person._db_values == expected_db_values

    def test_delete_attribute(self, defaults, mock_LDAP, person):
        """ Test delete LDAP attribute. """
        c = mock_LDAP
        expected_db_values = get_testable_values(person._db_values)

        # Replace the attribute.
        person.telephoneNumber = None
        person.save()

        # Simulate required attributes that should be added.
        person_attributes = {'telephoneNumber': None}

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.modify(
                'uid=tux,ou=People,dc=python-ldap,dc=org',
                {'telephoneNumber': ('MODIFY_DELETE', [])},
                mock.ANY,
            )
        ]
        c.assert_has_calls(expected_calls)

        # Assert caches are correct.
        assert person._alias == "default"
        assert person._dn == "uid=tux,ou=People,dc=python-ldap,dc=org"
        assert person._db_values == update_expected_db_values(
            expected_db_values, person_attributes)

        # Simulate failure.
        args, kwargs = c.modify.call_args
        onfailure = args[2]
        onfailure()

        # Assert caches are correct.
        assert person._alias == "default"
        assert person._dn == "uid=tux,ou=People,dc=python-ldap,dc=org"
        assert person._db_values == expected_db_values


class TestModelAccount:
    def test_set_primary_group(
            self, mock_LDAP, defaults, account1, group1):
        """ Test setting primary group for account. """
        c = mock_LDAP
        c.search = SearchMock()

        # Add person to group.
        account1.primary_group = group1
        account1.save()

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.modify(
                'uid=tux,ou=People,dc=python-ldap,dc=org',
                {'gidNumber': ('MODIFY_REPLACE', [b'10'])},
                mock.ANY,
            )
        ]
        c.assert_has_calls(expected_calls)

    def test_get_primary_group(
            self, mock_LDAP, defaults, account1, group1):
        """ Test getting primary group for account. """
        account1.primary_group = group1
        account1.save()

        c = mock_LDAP
        c.search = SearchMock()
        c.search.add_result("gidNumber=10", group1)

        # Get the primary group
        group = account1.primary_group.get()

        assert group == group1

    def test_add_secondary_group_existing(
            self, mock_LDAP, defaults, account1, group1):
        """ Test adding existing secondary group to account. """
        c = mock_LDAP
        c.search = SearchMock()

        # Add person to group.
        account1.secondary_groups.add(group1)
        account1.save()

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.modify(
                'cn=group1,ou=Group,dc=python-ldap,dc=org',
                {'memberUid': ('MODIFY_ADD', [b'tux'])},
                mock.ANY,
            )
        ]
        c.assert_has_calls(expected_calls)

    def test_add_secondary_group_new(
            self, mock_LDAP, defaults, account1):
        """ Test adding new secondary group to account. """
        c = mock_LDAP
        c.search = SearchMock()

        # Add person to group.
        account1.secondary_groups.create(cn="drwho", gidNumber=12)
        account1.save()

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.add(
                'cn=drwho,ou=Group,dc=python-ldap,dc=org',
                {
                    'gidNumber': [b'12'],
                    'objectClass': unordered_list([b'top', b'posixGroup']),
                    'memberUid': [b'tux'],
                    'cn': [b'drwho']
                },
                mock.ANY,
            )
        ]
        c.assert_has_calls(expected_calls)

    def test_remove_secondary_group(
            self, mock_LDAP, defaults, account1, group2):
        """ Test removing secondary group from account. """
        c = mock_LDAP
        c.search = SearchMock()

        # Add person to group.
        account1.secondary_groups.remove(group2)
        account1.save()

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.modify(
                'cn=group2,ou=Group,dc=python-ldap,dc=org',
                {'memberUid': ('MODIFY_DELETE', [])},
                mock.ANY,
            )
        ]
        c.assert_has_calls(expected_calls)

    def test_clear_secondary_group(
            self, mock_LDAP, defaults, account1, group2):
        """ Test removing all secondary groups from account. """
        c = mock_LDAP
        c.search = SearchMock()
        c.search.add_result("memberUid=tux", group2)

        # Add person to group.
        account1.secondary_groups.clear()
        account1.save()

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.modify(
                'cn=group2,ou=Group,dc=python-ldap,dc=org',
                {'memberUid': ('MODIFY_DELETE', [])},
                mock.ANY,
            )
        ]
        c.assert_has_calls(expected_calls)

    def test_get_secondary_group_none(
            self, mock_LDAP, defaults, account1):
        """ Test getting secondary group when none set. """
        c = mock_LDAP
        c.search = SearchMock()

        # Get the secondary groups.
        groups = list(account1.secondary_groups.all())
        assert groups == []

    def test_get_secondary_group_set(
            self, mock_LDAP, defaults, account1, group2):
        """ Test getting secondary group when one set. """
        c = mock_LDAP
        c.search = SearchMock()
        c.search.add_result("memberUid=tux", group2)

        # Get the secondary groups.
        groups = list(account1.secondary_groups.all())
        assert groups == [group2]


class TestModelGroup:
    def test_add_primary_account(
            self, mock_LDAP, defaults, account1, group1):
        """ Test add primary account to group. """
        c = mock_LDAP
        c.search = SearchMock()

        # Add person to group.
        group1.primary_accounts.add(account1)

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.modify(
                'uid=tux,ou=People,dc=python-ldap,dc=org',
                {'gidNumber': ('MODIFY_REPLACE', [b'10'])},
                mock.ANY,
            )
        ]
        c.assert_has_calls(expected_calls)

    def test_remove_primary_account(
            self, mock_LDAP, defaults, account1, group1):
        """ Test remove primary account from group. """
        account1.primary_group = group1
        account1.save()

        c = mock_LDAP
        c.search = SearchMock()

        # Remove person from primary group. This should fail, as all
        # accounts must have a primary group.
        with pytest.raises(tldap.exceptions.ValidationError):
            group1.primary_accounts.remove(account1)

        assert c.call_count == 0

    def test_get_primary_accounts(
            self, mock_LDAP, defaults, account1, group1):
        """ Test getting primary accounts from group. """
        account1.primary_group = group1
        account1.save()

        c = mock_LDAP
        c.search = SearchMock()
        c.search.add_result("gidNumber=10", account1)

        # Get the primary group
        accounts = list(group1.primary_accounts.all())

        assert accounts[0] == account1
        assert accounts == [account1]

    def test_add_secondary_account_existing(
            self, mock_LDAP, defaults, account1, group1):
        """ Test add existing secondary account to group. """
        c = mock_LDAP
        c.search = SearchMock()

        # Add person to group.
        group1.secondary_accounts.add(account1)
        group1.save()

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.modify(
                'cn=group1,ou=Group,dc=python-ldap,dc=org',
                {'memberUid': ('MODIFY_ADD', [b'tux'])},
                mock.ANY,
            )
        ]
        c.assert_has_calls(expected_calls)

    def test_add_secondary_account_new(
            self, mock_LDAP, defaults, group1):
        """ Test add new secondary account to group. """
        c = mock_LDAP
        c.search = SearchMock()
        account_attributes = dict(defaults.account_attributes)

        # Add person to group.
        group1.secondary_accounts.create(**defaults.account_attributes)
        group1.save()

        # Simulate required attributes that should be added.
        account_attributes.update({
            'objectClass':
                [b'inetOrgPerson', b'posixAccount', b'shadowAccount',
                    b'top', b'person', b'organizationalPerson'],
            'uidNumber': [b'1001'],
        })

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.add(
                'uid=tux,ou=People,dc=python-ldap,dc=org',
                get_expected_values(account_attributes),
                mock.ANY,
            ),
            mock.call.modify(
                'cn=group1,ou=Group,dc=python-ldap,dc=org',
                {'memberUid': ('MODIFY_ADD', [b'tux'])},
                mock.ANY,
            ),
        ]
        args, kwargs = c.add.call_args
        assert args[1] == get_expected_values(account_attributes)

        c.assert_has_calls(expected_calls)

    def test_remove_secondary_account(
            self, mock_LDAP, defaults, account1, group2):
        """ Test remove secondary account from group. """
        c = mock_LDAP
        c.search = SearchMock()

        # Add person to group.
        group2.secondary_accounts.remove(account1)
        group2.save()

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.modify(
                'cn=group2,ou=Group,dc=python-ldap,dc=org',
                {'memberUid': ('MODIFY_DELETE', [])},
                mock.ANY,
            )
        ]
        c.assert_has_calls(expected_calls)

    def test_clear_secondary_account(
            self, mock_LDAP, defaults, account1, group2):
        """ Test remove all secondary accounts from group. """
        c = mock_LDAP
        c.search = SearchMock()

        # Add person to group.
        group2.secondary_accounts.clear()
        group2.save()

        # Assert that we made the correct calls to the backend.
        expected_calls = [
            mock.call.modify(
                'cn=group2,ou=Group,dc=python-ldap,dc=org',
                {'memberUid': ('MODIFY_DELETE', [])},
                mock.ANY,
            )
        ]
        c.assert_has_calls(expected_calls)

    def test_get_secondary_accounts_none(
            self, mock_LDAP, defaults, group1):
        """ Test get all secondary accounts when none set. """
        c = mock_LDAP
        c.search = SearchMock()

        # Get the secondary groups.
        accounts = list(group1.secondary_accounts.all())
        assert accounts == []

    def test_get_secondary_accounts_set(
            self, mock_LDAP, defaults, account1, group2):
        """ Test get all secondary accounts when one set. """
        c = mock_LDAP
        c.search = SearchMock()
        c.search.add_result("uid=tux", account1)

        # Get the secondary groups.
        accounts = list(group2.secondary_accounts.all())
        assert accounts == [account1]


class TestModelQuery:
    def test_query_get_person(self, mock_LDAP, person, defaults):
        """ Test getting a person. """
        c = mock_LDAP
        c.search = SearchMock()
        c.search.add_result(
            "entryDN:=uid=tux, ou=People, dc=python-ldap,dc=org", person)

        person = defaults.person.objects.get(
            dn="uid=tux, ou=People, dc=python-ldap,dc=org")
        assert person.uid == "tux"

    def test_filter_normal(self, defaults):
        """ Test filter. """
        ldap_filter = defaults.person.objects.all()._get_filter(
            tldap.Q(uid='tux'))
        assert ldap_filter == "(uid=tux)"

    def test_filter_backslash(self, defaults):
        """ Test filter with backslash. """
        ldap_filter = defaults.person.objects.all()._get_filter(
            tldap.Q(uid='t\\ux'))
        assert ldap_filter == "(uid=t\\5cux)"

    def test_filter_negated(self, defaults):
        """ Test filter with negated value. """
        ldap_filter = defaults.person.objects.all()._get_filter(
            ~tldap.Q(uid='tux'))
        assert ldap_filter == "(!(uid=tux))"

    def test_filter_or_2(self, defaults):
        """ Test filter with OR condition. """
        ldap_filter = defaults.person.objects.all()._get_filter(
            tldap.Q(uid='tux') | tldap.Q(uid='tuz'))
        assert ldap_filter == "(|(uid=tux)(uid=tuz))"

    def test_filter_or_3(self, defaults):
        """ Test filter with OR condition """
        ldap_filter = defaults.person.objects.all()._get_filter(
            tldap.Q() | tldap.Q(uid='tux') | tldap.Q(uid='tuz'))
        assert ldap_filter == "(|(uid=tux)(uid=tuz))"

    def test_filter_and(self, defaults):
        """ Test filter with AND condition. """
        ldap_filter = defaults.person.objects.all()._get_filter(
            tldap.Q() & tldap.Q(uid='tux') & tldap.Q(uid='tuz'))
        assert ldap_filter == "(&(uid=tux)(uid=tuz))"

    def test_filter_and_or(self, defaults):
        """ Test filter with AND and OR condition. """
        ldap_filter = defaults.person.objects.all()._get_filter(
            tldap.Q(uid='tux') & (tldap.Q(uid='tuz') | tldap.Q(uid='meow')))
        assert ldap_filter == "(&(uid=tux)(|(uid=tuz)(uid=meow)))"
