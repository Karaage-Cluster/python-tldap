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

import pytest
import mock
from mock import call, ANY

import tldap
import tldap.schemas.rfc
import tldap.transaction
import tldap.exceptions
import tldap.modlist

import tldap.test.slapd

import ldap3
import ldap3.core.exceptions as errors

server = None


NO_SUCH_OBJECT = ldap3.core.exceptions.LDAPNoSuchObjectResult


class Defaults:
    pass


class ServerComparer:
    def __init__(self, server):
        self._server = server
        assert isinstance(server, ldap3.Server)

    def __eq__(self, other):
        if not isinstance(other, ldap3.Server):
            return False
        if self._server.name != other.name:
            return False
        return True


class MockSearchResponse:
    def __init__(self):
        self.response = []

    def add(self, dn, db_values):
        self.response.append({
            'type': 'searchResEntry',
            'dn': dn,
            'raw_attributes': db_values,
        })

    def __getitem__(self, key):
        return self.response[key]

    def __iter__(self):
        return iter(self.response)

    def __len__(self):
        return len(self.response)


@pytest.fixture
def search_response():
    return MockSearchResponse()


@pytest.fixture
def defaults(search_response):
    """ Get globals for all model tests. """

    values = Defaults()
    values.modlist = tldap.modlist.addModlist({
        'givenName': [b"Tux"],
        'sn': [b"Torvalds"],
        'cn': [b"Tux Torvalds"],
        'telephoneNumber': [b"000"],
        'mail': [b"tuz@example.org"],
        'o': [b"Linux Rules"],
        'userPassword': [b"silly"],
        'objectClass': [
            b'top', b'person', b'organizationalPerson', b'inetOrgPerson'],
    })

    values.mock_connection = mock.MagicMock()
    values.mock_connection.response = search_response

    values.mock_class = mock.MagicMock()
    values.mock_class.return_value = values.mock_connection

    LDAP = {
        'default': {
            'ENGINE': 'tldap.backend.fake_transactions',
            'URI': 'ldap://localhost:38911/',
            'USER': 'cn=Manager,dc=python-ldap,dc=org',
            'PASSWORD': 'password',
            'USE_TLS': False,
            'TLS_CA': None,
            'LDAP_ACCOUNT_BASE': 'ou=People, dc=python-ldap,dc=org',
            'LDAP_GROUP_BASE': 'ou=Group, dc=python-ldap,dc=org'
        }
    }

    tldap.setup(LDAP)

    c = tldap.connection
    c.set_connection_class(values.mock_class)

    values.expected_server = ServerComparer(ldap3.Server(
        host='localhost',
        port=38911,
        use_ssl=False,
        allowed_referral_hosts=[('*', True)],
        get_info='NO_INFO'))

    assert c._transact is False
    assert c._onrollback == []

    yield values

    assert c._transact is False
    assert c._onrollback == []


class TestBackendBase:
    def test_check_password_correct(self, defaults):
        """ Test if we can logon correctly with correct password. """
        result = tldap.connection.check_password(
            'cn=Manager,dc=python-ldap,dc=org',
            'password'
        )
        assert result is True

        defaults.mock_class.assert_called_once_with(
            defaults.expected_server,
            authentication='SIMPLE',
            password='password',
            user='cn=Manager,dc=python-ldap,dc=org')

        expected_calls = [call.open(), call.bind(), call.unbind()]
        defaults.mock_connection.assert_has_calls(expected_calls)

    def test_check_password_wrong(self, defaults):
        """ Test that we can't logon correctly with wrong password. """
        defaults.mock_connection.bind.side_effect = \
            errors.LDAPInvalidCredentialsResult()

        result = tldap.connection.check_password(
            'cn=Manager,dc=python-ldap,dc=org',
            'password2'
        )
        assert result is False

        defaults.mock_class.assert_called_once_with(
            defaults.expected_server,
            authentication='SIMPLE',
            password='password2',
            user='cn=Manager,dc=python-ldap,dc=org')

        expected_calls = [call.open(), call.bind(), call.unbind()]
        defaults.mock_connection.assert_has_calls(expected_calls)

    def test_search(self, search_response, defaults):
        """ Test base search scope. """
        dn = 'uid=tux,ou=People,dc=python-ldap,dc=org'
        search_response.add(dn, defaults.modlist)
        search_response.add(dn, defaults.modlist)

        c = tldap.connection
        mock_dn = mock.Mock()
        mock_scope = mock.Mock()
        mock_filter = mock.Mock()
        mock_limit = mock.Mock()
        r = c.search(mock_dn, mock_scope, mock_filter, limit=mock_limit)

        assert next(r)[1] == defaults.modlist
        assert next(r)[1] == defaults.modlist

        with pytest.raises(StopIteration):
            next(r)

        expected_calls = [
            call.open(),
            call.bind(),
            call.search(
                mock_dn, mock_filter, mock_scope,
                attributes=ANY, paged_size=mock_limit),
        ]
        defaults.mock_connection.assert_has_calls(expected_calls)


class TestBackendFakeTransactions:
    def test_roll_back_explicit(self, search_response, defaults):
        """ Test explicit roll back. """
        dn = 'uid=tux,ou=People,dc=python-ldap,dc=org'
        search_response.add(dn, defaults.modlist)

        c = tldap.connection
        onfailure = mock.Mock()
        with tldap.transaction.commit_on_success():
            c.add(dn, defaults.modlist)
            c.modify(dn, {
                'sn': (ldap3.MODIFY_REPLACE, [b"Gates"])},
                onfailure=onfailure)
            c.rollback()

        onfailure.assert_called_once_with()
        expected_calls = [
            call.open(),
            call.bind(),
            call.add(dn, None, defaults.modlist),
            call.search(dn, '(objectclass=*)', 'BASE', attributes=ANY),
            call.modify(dn, {'sn': ('MODIFY_REPLACE', [b'Gates'])}),
            call.modify(dn, {'sn': ('MODIFY_REPLACE', [b'Torvalds'])}),
            call.delete(dn)
        ]
        defaults.mock_connection.assert_has_calls(expected_calls)

    def test_roll_back_exception(self, search_response, defaults):
        """ Test roll back on exception. """
        dn = 'uid=tux,ou=People,dc=python-ldap,dc=org'
        search_response.add(dn, defaults.modlist)

        c = tldap.connection
        onfailure = mock.Mock()
        with pytest.raises(RuntimeError):
            with tldap.transaction.commit_on_success():
                c.add(dn, defaults.modlist)
                c.modify(dn, {
                    'sn': (ldap3.MODIFY_REPLACE, [b"Gates"])},
                    onfailure)
                raise RuntimeError("testing failure")

        onfailure.assert_called_once_with()
        expected_calls = [
            call.open(),
            call.bind(),
            call.add(dn, None, defaults.modlist),
            call.search(dn, '(objectclass=*)', 'BASE', attributes=ANY),
            call.modify(dn, {'sn': ('MODIFY_REPLACE', [b'Gates'])}),
            call.modify(dn, {'sn': ('MODIFY_REPLACE', [b'Torvalds'])}),
            call.delete(dn)
        ]
        defaults.mock_connection.assert_has_calls(expected_calls)

    def test_replace_attribute_rollback(self, search_response, defaults):
        """ Test replace attribute with explicit roll back. """
        dn = 'uid=tux,ou=People,dc=python-ldap,dc=org'
        search_response.add(dn, defaults.modlist)

        c = tldap.connection
        onfailure = mock.Mock()
        c.add(dn, defaults.modlist)
        with pytest.raises(tldap.exceptions.TestFailure):
            with tldap.transaction.commit_on_success():
                c.modify(dn, {
                    'sn': (ldap3.MODIFY_REPLACE, [b"Gates"])},
                    onfailure=onfailure)
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()

        onfailure.assert_called_once_with()
        expected_calls = [
            call.open(),
            call.bind(),
            call.add(dn, None, defaults.modlist),
            call.search(dn, '(objectclass=*)', 'BASE', attributes=ANY),
            call.modify(dn, {'sn': ('MODIFY_REPLACE', [b'Gates'])}),
            call.modify(dn, {'sn': ('MODIFY_REPLACE', [b'Torvalds'])}),
        ]
        defaults.mock_connection.assert_has_calls(expected_calls)

    def test_replace_attribute_success(self, search_response, defaults):
        """ Test change attribute with success. """
        dn = 'uid=tux,ou=People,dc=python-ldap,dc=org'
        search_response.add(dn, defaults.modlist)

        c = tldap.connection
        onfailure = mock.Mock()
        c.add(dn, defaults.modlist)
        with tldap.transaction.commit_on_success():
            c.modify(dn, {
                'sn': (ldap3.MODIFY_REPLACE, [b"Gates"])},
                onfailure=onfailure)

        onfailure.assert_not_called()
        expected_calls = [
            call.open(),
            call.bind(),
            call.add(dn, None, defaults.modlist),
            call.search(dn, '(objectclass=*)', 'BASE', attributes=ANY),
            call.modify(dn, {'sn': ('MODIFY_REPLACE', [b'Gates'])}),
        ]
        defaults.mock_connection.assert_has_calls(expected_calls)

    def test_replace_attribute_list_rollback(self, search_response, defaults):
        """ Test replacing attribute with rollback. """
        dn = 'uid=tux,ou=People,dc=python-ldap,dc=org'
        search_response.add(dn, defaults.modlist)

        c = tldap.connection
        onfailure = mock.Mock()
        c.add(dn, defaults.modlist)
        with pytest.raises(tldap.exceptions.TestFailure):
            with tldap.transaction.commit_on_success():
                c.modify(dn, {
                    "telephoneNumber": (ldap3.MODIFY_REPLACE, [b"222"])},
                    onfailure=onfailure)
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()

        onfailure.assert_called_once_with()
        expected_calls = [
            call.open(),
            call.bind(),
            call.add(dn, None, defaults.modlist),
            call.search(dn, '(objectclass=*)', 'BASE', attributes=ANY),
            call.modify(dn, {'telephoneNumber': ('MODIFY_REPLACE', [b'222'])}),
            call.modify(dn, {'telephoneNumber': ('MODIFY_REPLACE', [b'000'])}),
        ]
        defaults.mock_connection.assert_has_calls(expected_calls)

    def test_replace_attribute_list_success(self, search_response, defaults):
        """ Test replacing attribute with success. """
        dn = 'uid=tux,ou=People,dc=python-ldap,dc=org'
        search_response.add(dn, defaults.modlist)

        c = tldap.connection
        onfailure = mock.Mock()
        c.add(dn, defaults.modlist)
        with tldap.transaction.commit_on_success():
            c.modify(dn, {
                'telephoneNumber': (ldap3.MODIFY_REPLACE, [b"222"])},
                onfailure=onfailure)

        onfailure.assert_not_called()
        expected_calls = [
            call.open(),
            call.bind(),
            call.add(dn, None, defaults.modlist),
            call.search(dn, '(objectclass=*)', 'BASE', attributes=ANY),
            call.modify(dn, {'telephoneNumber': ('MODIFY_REPLACE', [b'222'])}),
        ]
        defaults.mock_connection.assert_has_calls(expected_calls)

    def test_delete_attribute_rollback(self, search_response, defaults):
        """ Test deleting attribute *of new object* with rollback. """
        dn = 'uid=tux,ou=People,dc=python-ldap,dc=org'
        search_response.add(dn, defaults.modlist)

        c = tldap.connection
        onfailure = mock.Mock()
        c.add(dn, defaults.modlist)
        with pytest.raises(tldap.exceptions.TestFailure):
            with tldap.transaction.commit_on_success():
                c.modify(dn, {
                    "telephoneNumber": (ldap3.MODIFY_DELETE, [b'000'])},
                    onfailure=onfailure)
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()

        onfailure.assert_called_once_with()
        expected_calls = [
            call.open(),
            call.bind(),
            call.add(dn, None, defaults.modlist),
            call.search(dn, '(objectclass=*)', 'BASE', attributes=ANY),
            call.modify(dn, {'telephoneNumber': ('MODIFY_DELETE', [b'000'])}),
            call.modify(dn, {'telephoneNumber': ('MODIFY_ADD', [b'000'])}),
        ]
        defaults.mock_connection.assert_has_calls(expected_calls)

    def test_delete_attribute_success(self, search_response, defaults):
        """ Test deleting attribute *of new object* with success. """
        dn = 'uid=tux,ou=People,dc=python-ldap,dc=org'
        search_response.add(dn, defaults.modlist)

        c = tldap.connection
        onfailure = mock.Mock()
        c.add(dn, defaults.modlist)
        with tldap.transaction.commit_on_success():
            c.modify(dn, {
                "telephoneNumber": (ldap3.MODIFY_DELETE, [b'000'])},
                onfailure=onfailure)

        onfailure.assert_not_called()
        expected_calls = [
            call.open(),
            call.bind(),
            call.add(dn, None, defaults.modlist),
            call.search(dn, '(objectclass=*)', 'BASE', attributes=ANY),
            call.modify(dn, {'telephoneNumber': ('MODIFY_DELETE', [b'000'])}),
        ]
        defaults.mock_connection.assert_has_calls(expected_calls)

    def test_add_attribute_rollback(self, search_response, defaults):
        """ Test adding attribute with rollback. """
        dn = 'uid=tux,ou=People,dc=python-ldap,dc=org'
        search_response.add(dn, defaults.modlist)

        c = tldap.connection
        onfailure = mock.Mock()
        c.add(dn, defaults.modlist)
        with pytest.raises(tldap.exceptions.TestFailure):
            with tldap.transaction.commit_on_success():
                c.modify(dn, {
                    "telephoneNumber": (ldap3.MODIFY_ADD, [b"111"])},
                    onfailure=onfailure)
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()

        onfailure.assert_called_once_with()
        expected_calls = [
            call.open(),
            call.bind(),
            call.add(dn, None, defaults.modlist),
            call.search(dn, '(objectclass=*)', 'BASE', attributes=ANY),
            call.modify(dn, {'telephoneNumber': ('MODIFY_ADD', [b'111'])}),
            call.modify(dn, {'telephoneNumber': ('MODIFY_DELETE', [b'111'])}),
        ]
        defaults.mock_connection.assert_has_calls(expected_calls)

    def test_add_attribute_success(
            self, search_response, defaults):
        """ Test adding attribute with success. """
        dn = 'uid=tux,ou=People,dc=python-ldap,dc=org'
        search_response.add(dn, defaults.modlist)

        c = tldap.connection
        onfailure = mock.Mock()
        c.add(dn, defaults.modlist)
        with tldap.transaction.commit_on_success():
            c.modify(dn, {
                'telephoneNumber': (ldap3.MODIFY_ADD, [b"111"])},
                onfailure=onfailure)

        onfailure.assert_not_called()
        expected_calls = [
            call.open(),
            call.bind(),
            call.add(dn, None, defaults.modlist),
            call.search(dn, '(objectclass=*)', 'BASE', attributes=ANY),
            call.modify(dn, {'telephoneNumber': ('MODIFY_ADD', [b'111'])}),
        ]
        defaults.mock_connection.assert_has_calls(expected_calls)

    def test_third_statement_fails(self, search_response, defaults):
        """
        Test success when 3rd statement fails;

        Need to roll back 2nd and 1st statements
        """
        dn = 'uid=tux,ou=People,dc=python-ldap,dc=org'
        search_response.add(dn, defaults.modlist)

        c = tldap.connection
        onfailure = mock.Mock()
        c.add(dn, defaults.modlist)
        with pytest.raises(tldap.exceptions.TestFailure):
            with tldap.transaction.commit_on_success():
                c.modify(dn, {
                    "sn": (ldap3.MODIFY_REPLACE, b"Milkshakes")},
                    onfailure=onfailure)
                c.modify(dn, {
                    "sn": (ldap3.MODIFY_REPLACE, [b"Bannas"])},
                    onfailure=onfailure)
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()

        onfailure.assert_has_calls([call(), call()])
        expected_calls = [
            call.open(),
            call.bind(),
            call.add(dn, None, defaults.modlist),
            call.search(dn, '(objectclass=*)', 'BASE', attributes=ANY),
            call.modify(dn, {'sn': ('MODIFY_REPLACE', b'Milkshakes')}),
            call.search(dn, '(objectclass=*)', 'BASE', attributes=ANY),
            call.modify(dn, {'sn': ('MODIFY_REPLACE', [b'Bannas'])}),
        ]
        defaults.mock_connection.assert_has_calls(expected_calls)

    def test_rename_rollback(self, search_response, defaults):
        """ Test rename with rollback. """
        dn = 'uid=tux,ou=People,dc=python-ldap,dc=org'
        dn2 = 'uid=tuz,ou=People,dc=python-ldap,dc=org'
        search_response.add(dn, defaults.modlist)

        c = tldap.connection
        onfailure = mock.Mock()
        c.add(dn, defaults.modlist)
        with pytest.raises(tldap.exceptions.TestFailure):
            with tldap.transaction.commit_on_success():
                c.rename(
                    dn, 'uid=tuz',
                    onfailure=onfailure)
                c.modify(dn2, {
                    "sn": (ldap3.MODIFY_REPLACE, [b"Tuz"])})
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()

        onfailure.assert_called_once_with()
        expected_calls = [
            call.open(),
            call.bind(),
            call.add(dn, None, defaults.modlist),
            call.modify_dn(dn, 'uid=tuz', new_superior=None),
            call.search(dn2, '(objectclass=*)', 'BASE', attributes=ANY),
            call.modify(dn2, {'sn': ('MODIFY_REPLACE', [b'Tuz'])}),
            call.modify(dn2, {'sn': ('MODIFY_REPLACE', [b'Torvalds'])}),
            call.modify_dn(dn2, 'uid=tux', new_superior=None),
        ]
        defaults.mock_connection.assert_has_calls(expected_calls)

    def test_rename_success(self, search_response, defaults):
        """ Test rename with success. """
        dn = 'uid=tux,ou=People,dc=python-ldap,dc=org'
        dn2 = 'uid=tuz,ou=People,dc=python-ldap,dc=org'
        search_response.add(dn, defaults.modlist)

        c = tldap.connection
        onfailure = mock.Mock()
        c.add(dn, defaults.modlist)
        with tldap.transaction.commit_on_success():
            c.rename(
                dn, 'uid=tuz',
                onfailure=onfailure)
            c.modify(dn2, {
                'sn': (ldap3.MODIFY_REPLACE, [b"Tuz"])})

        onfailure.assert_not_called()
        expected_calls = [
            call.open(),
            call.bind(),
            call.add(dn, None, defaults.modlist),
            call.modify_dn(dn, 'uid=tuz', new_superior=None),
            call.search(dn2, '(objectclass=*)', 'BASE', attributes=ANY),
            call.modify(dn2, {'sn': ('MODIFY_REPLACE', [b'Tuz'])}),
        ]
        defaults.mock_connection.assert_has_calls(expected_calls)

    def test_move_rollback(self, search_response, defaults):
        """ Test move with rollback. """
        dn = 'uid=tux,ou=People,dc=python-ldap,dc=org'
        dn2 = 'uid=tux,ou=Groups,dc=python-ldap,dc=org'
        old_base = 'ou=People,dc=python-ldap,dc=org'
        new_base = 'ou=Groups,dc=python-ldap,dc=org'
        search_response.add(dn, defaults.modlist)

        c = tldap.connection
        onfailure = mock.Mock()
        c.add(dn, defaults.modlist)
        with pytest.raises(tldap.exceptions.TestFailure):
            with tldap.transaction.commit_on_success():
                c.rename(
                    dn,
                    "uid=tux", "ou=Groups,dc=python-ldap,dc=org",
                    onfailure=onfailure)
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()

        onfailure.assert_called_once_with()
        expected_calls = [
            call.open(),
            call.bind(),
            call.add(dn, None, defaults.modlist),
            call.modify_dn(dn, 'uid=tux', new_superior=new_base),
            call.modify_dn(dn2, 'uid=tux', new_superior=old_base),
        ]
        defaults.mock_connection.assert_has_calls(expected_calls)

    def test_move_success(self, search_response, defaults):
        """ Test move with success. """
        dn = 'uid=tux,ou=People,dc=python-ldap,dc=org'
        new_base = 'ou=Groups,dc=python-ldap,dc=org'
        search_response.add(dn, defaults.modlist)

        c = tldap.connection
        onfailure = mock.Mock()
        c.add(dn, defaults.modlist)
        with tldap.transaction.commit_on_success():
            c.rename(
                dn,
                "uid=tux", new_base,
                onfailure=onfailure)

        onfailure.assert_not_called()
        expected_calls = [
            call.open(),
            call.bind(),
            call.add(dn, None, defaults.modlist),
            call.modify_dn(dn, 'uid=tux', new_superior=new_base),
        ]
        defaults.mock_connection.assert_has_calls(expected_calls)

    def test_delete_rollback(self, search_response, defaults):
        """ Test delete rollback. """
        dn = 'uid=tux,ou=People,dc=python-ldap,dc=org'
        search_response.add(dn, defaults.modlist)

        c = tldap.connection
        onfailure = mock.Mock()
        c.add(dn, defaults.modlist)
        with pytest.raises(tldap.exceptions.TestFailure):
            with tldap.transaction.commit_on_success():
                c.delete(dn, onfailure=onfailure)
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()

        onfailure.assert_called_once_with()
        expected_calls = [
            call.open(),
            call.bind(),
            call.add(dn, None, defaults.modlist),
            call.search(dn, '(objectclass=*)', 'BASE', attributes=ANY),
            call.delete(dn),
            call.add(dn, None, defaults.modlist),
        ]
        defaults.mock_connection.assert_has_calls(expected_calls)

    def test_delete_success(self, search_response, defaults):
        """ Test delete success. """
        dn = 'uid=tux,ou=People,dc=python-ldap,dc=org'
        search_response.add(dn, defaults.modlist)

        c = tldap.connection
        onfailure = mock.Mock()
        c.add(dn, defaults.modlist)
        with tldap.transaction.commit_on_success():
            c.delete(dn, onfailure=onfailure)

        onfailure.assert_not_called()
        expected_calls = [
            call.open(),
            call.bind(),
            call.add(dn, None, defaults.modlist),
            call.search(dn, '(objectclass=*)', 'BASE', attributes=ANY),
            call.delete(dn),
        ]
        defaults.mock_connection.assert_has_calls(expected_calls)
