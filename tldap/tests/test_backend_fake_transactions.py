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

import tldap
import tldap.schemas.rfc
import tldap.transaction
import tldap.exceptions
import tldap.modlist

import tldap.test.slapd
import tldap.tests.base as base

import ldap3
import ldap3.core.exceptions
from ..compat import SUBTREE, LEVEL, BASE

server = None


NO_SUCH_OBJECT = ldap3.core.exceptions.LDAPNoSuchObjectResult


class BackendTest(base.LdapTestCase):
    def setUp(self):
        super(BackendTest, self).setUp()

        self.modlist = tldap.modlist.addModlist({
            'givenName': ["Tux"],
            'sn': ["Torvalds"],
            'cn': ["Tux Torvalds"],
            'telephoneNumber': ["000"],
            'mail': ["tuz@example.org"],
            'o': ["Linux Rules"],
            'userPassword': ["silly"],
            'objectClass': [
                'top', 'person', 'organizationalPerson', 'inetOrgPerson'],
        })

        c = tldap.connection
        c.add("ou=People, dc=python-ldap,dc=org", self.modlist)
        c.add("ou=Groups, dc=python-ldap,dc=org", {
            "objectClass": ["top", "organizationalunit"]
        })
        self.assertEqual(c._transact, False)
        self.assertEqual(c._onrollback, [])

    def tearDown(self):
        c = tldap.connection
        self.assertEqual(c._transact, False)
        self.assertEqual(c._onrollback, [])

    def get(self, c, base):
        """
        returns ldap object for search_string
        raises MultipleResultsException if more than one
        entry exists for given search string
        """
        result_data = list(c.search(base, BASE))
        no_results = len(result_data)
        self.assertEqual(no_results, 1)
        return result_data[0][1]

    def assert_dn_exists(self, dn):
        c = tldap.connection
        self.get(c, dn)

    def assert_dn_not_exists(self, dn):
        c = tldap.connection
        self.assertRaises(NO_SUCH_OBJECT, self.get, c, dn)

    def test_check_password_correct(self):
        """ Test if we can logon correctly with correct password. """
        result = tldap.connection.check_password(
            'cn=Manager,dc=python-ldap,dc=org',
            'password'
        )
        self.assertEqual(result, True)

    def test_check_password_wrong(self):
        """ Test that we can't logon correctly with wrong password. """
        result = tldap.connection.check_password(
            'cn=Manager,dc=python-ldap,dc=org',
            'password2'
        )
        self.assertEqual(result, False)

    def test_transaction_explicit_roll_back(self):
        """ Test explicit roll back. """
        c = tldap.connection
        onfailure = mock.Mock()
        with tldap.transaction.commit_on_success():
            c.add("uid=tux, ou=People, dc=python-ldap,dc=org",
                  self.modlist)
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", {
                'sn': (ldap3.MODIFY_REPLACE, "Gates")},
                onfailure=onfailure)
            c.rollback()
        self.assert_dn_not_exists("uid=tux, ou=People, dc=python-ldap,dc=org")
        onfailure.assert_called_once_with()

    def test_transaction_explicit_roll_back_on_exception(self):
        """ Test roll back on exception. """
        c = tldap.connection
        onfailure = mock.Mock()
        try:
            with tldap.transaction.commit_on_success():
                c.add(
                    "uid=tux, ou=People, dc=python-ldap,dc=org", self.modlist)
                c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", {
                    'sn': (ldap3.MODIFY_REPLACE, "Gates")},
                    onfailure)
                raise RuntimeError("testing failure")
        except RuntimeError:
            pass
        self.assert_dn_not_exists("uid=tux, ou=People, dc=python-ldap,dc=org")
        onfailure.assert_called_once_with()

    def test_transaction_replace_attribute_rollback(self):
        """ Test explicit roll back. """
        c = tldap.connection
        onfailure = mock.Mock()
        c.add("uid=tux, ou=People, dc=python-ldap,dc=org", self.modlist)
        try:
            with tldap.transaction.commit_on_success():
                c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", {
                    'sn': (ldap3.MODIFY_REPLACE, "Gates")},
                    onfailure=onfailure)
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()
        except tldap.exceptions.TestFailure:
            pass
        else:
            self.fail("Exception not generated")
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'],
            [b"Torvalds"])
        onfailure.assert_called_once_with()

    def test_transaction_replace_attribute_success(self):
        """ Test success commits. """
        c = tldap.connection
        onfailure = mock.Mock()
        c.add("uid=tux, ou=People, dc=python-ldap,dc=org", self.modlist)
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", {
                'sn': (ldap3.MODIFY_REPLACE, "Gates")},
                onfailure=onfailure)
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [b"Gates"])
        onfailure.assert_not_called()

    def test_transaction_replace_attribute_list_rollback(self):
        """ Test replacing attribute with rollback. """
        c = tldap.connection
        onfailure = mock.Mock()
        c.add("uid=tux, ou=People, dc=python-ldap,dc=org", self.modlist)
        try:
            with tldap.transaction.commit_on_success():
                c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", {
                    "telephoneNumber": (ldap3.MODIFY_REPLACE, ["222"])},
                    onfailure=onfailure)
                self.assertEqual(self.get(
                    c, "uid=tux, ou=People, dc=python-ldap,dc=org")[
                    'telephoneNumber'],
                    [b"222"])
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()
        except tldap.exceptions.TestFailure:
            pass
        else:
            self.fail("Exception not generated")
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'],
            [b"000"])
        onfailure.assert_called_once_with()

    def test_transaction_replace_attribute_list_success(self):
        """ Test replacing attribute with success. """
        c = tldap.connection
        onfailure = mock.Mock()
        c.add("uid=tux, ou=People, dc=python-ldap,dc=org", self.modlist)
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", {
                'telephoneNumber': (ldap3.MODIFY_REPLACE, "222")},
                onfailure=onfailure)
            self.assertEqual(self.get(
                c, "uid=tux, ou=People, dc=python-ldap,dc=org")[
                'telephoneNumber'],
                [b"222"])
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'],
            [b"222"])
        onfailure.assert_not_called()

    def test_transaction_delete_attribute_rollback(self):
        """ Test deleting attribute *of new object* with rollback. """
        c = tldap.connection
        onfailure = mock.Mock()
        c.add("uid=tux, ou=People, dc=python-ldap,dc=org", self.modlist)
        try:
            with tldap.transaction.commit_on_success():
                c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", {
                    "telephoneNumber": (ldap3.MODIFY_DELETE, ['000'])},
                    onfailure=onfailure)
                self.assertRaises(KeyError, lambda: self.get(
                    c, "uid=tux, ou=People, dc=python-ldap,dc=org")[
                    'telephoneNumber'])
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()
        except tldap.exceptions.TestFailure:
            pass
        else:
            self.fail("Exception not generated")
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'],
            [b"000"])
        onfailure.assert_called_once_with()

    def test_transaction_delete_attribute_success(self):
        """ Test deleting attribute *of new object* with success. """
        c = tldap.connection
        onfailure = mock.Mock()
        c.add("uid=tux, ou=People, dc=python-ldap,dc=org", self.modlist)
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", {
                "telephoneNumber": (ldap3.MODIFY_DELETE, ['000'])},
                onfailure=onfailure)
            self.assertRaises(KeyError, lambda: self.get(
                c, "uid=tux, ou=People, dc=python-ldap,dc=org")[
                'telephoneNumber'])
        self.assertRaises(KeyError, lambda: self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'])
        onfailure.assert_not_called()

    def test_transaction_add_attribute_rollback(self):
        """ Test adding attribute with rollback. """
        c = tldap.connection
        onfailure = mock.Mock()
        c.add("uid=tux, ou=People, dc=python-ldap,dc=org", self.modlist)
        try:
            with tldap.transaction.commit_on_success():
                c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", {
                    "telephoneNumber": (ldap3.MODIFY_ADD, ["111"])},
                    onfailure=onfailure)
                self.assertEqual(self.get(
                    c, "uid=tux, ou=People, dc=python-ldap,dc=org")[
                    'telephoneNumber'],
                    [b"000", b"111"])
                self.assertRaises(
                    ldap3.core.exceptions.LDAPAttributeOrValueExistsResult,
                    lambda: c.modify(
                        "uid=tux, ou=People, dc=python-ldap,dc=org", {
                            'telephoneNumber': (ldap3.MODIFY_ADD, ["111"])})
                )
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()
        except tldap.exceptions.TestFailure:
            pass
        else:
            self.fail("Exception not generated")
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'],
            [b"000"])
        onfailure.assert_called_once_with()

    def test_transaction_add_attribute_success(self):
        """ Test adding attribute with success. """
        c = tldap.connection
        onfailure = mock.Mock()
        c.add("uid=tux, ou=People, dc=python-ldap,dc=org", self.modlist)
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", {
                'telephoneNumber': (ldap3.MODIFY_ADD, ["111"])},
                onfailure=onfailure)
            self.assertEqual(self.get(
                c, "uid=tux, ou=People, dc=python-ldap,dc=org")[
                'telephoneNumber'], [b"000", b"111"])
            self.assertRaises(
                ldap3.core.exceptions.LDAPAttributeOrValueExistsResult,
                lambda: c.modify(
                    "uid=tux, ou=People, dc=python-ldap,dc=org", {
                        'telephoneNumber': (ldap3.MODIFY_ADD, ["111"])})
            )
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'],
            [b"000", b"111"])
        onfailure.assert_not_called()

    def test_search_base(self):
        """ Test base search scope. """
        c = tldap.connection
        c.add("uid=tux, ou=People, dc=python-ldap,dc=org", self.modlist)
        r = c.search(
            "uid=tux, ou=People, dc=python-ldap,dc=org",
            BASE, "(uid=tux)")
        self.assertEqual(len(list(r)), 1)
        r = c.search(
            "ou=People, dc=python-ldap,dc=org",
            BASE, "(uid=tux)")
        self.assertEqual(len(list(r)), 0)
        r = c.search(
            "dc=python-ldap,dc=org",
            BASE, "(uid=tux)")
        self.assertEqual(len(list(r)), 0)
        r = c.search(
            "ou=Groups, dc=python-ldap,dc=org",
            BASE, "(uid=tux)")
        self.assertEqual(len(list(r)), 0)
        r = c.search(
            "dc=python-ldap,dc=org",
            BASE, "(uid=tux)")
        self.assertEqual(len(list(r)), 0)

    def test_search_level(self):
        """ Test level search scope. """
        c = tldap.connection
        c.add("uid=tux, ou=People, dc=python-ldap,dc=org", self.modlist)
        r = c.search(
            "uid=tux, ou=People, dc=python-ldap,dc=org",
            LEVEL, "(uid=tux)")
        self.assertEqual(len(list(r)), 0)
        r = c.search(
            "ou=People, dc=python-ldap,dc=org",
            LEVEL, "(uid=tux)")
        self.assertEqual(len(list(r)), 1)
        r = c.search(
            "dc=python-ldap,dc=org",
            LEVEL, "(uid=tux)")
        self.assertEqual(len(list(r)), 0)
        r = c.search(
            "ou=Groups, dc=python-ldap,dc=org",
            LEVEL, "(uid=tux)")
        self.assertEqual(len(list(r)), 0)
        r = c.search(
            "dc=python-ldap,dc=org",
            BASE, "(uid=tux)")
        self.assertEqual(len(list(r)), 0)

    def test_search_subtree(self):
        """ Test subtree search scope. """
        c = tldap.connection
        c.add("uid=tux, ou=People, dc=python-ldap,dc=org", self.modlist)
        r = c.search(
            "uid=tux, ou=People, dc=python-ldap,dc=org",
            SUBTREE, "(uid=tux)")
        self.assertEqual(len(list(r)), 1)
        r = c.search(
            "ou=People, dc=python-ldap,dc=org",
            SUBTREE, "(uid=tux)")
        self.assertEqual(len(list(r)), 1)
        r = c.search(
            "dc=python-ldap,dc=org",
            SUBTREE, "(uid=tux)")
        self.assertEqual(len(list(r)), 1)
        r = c.search(
            "ou=Groups, dc=python-ldap,dc=org",
            SUBTREE, "(uid=tux)")
        self.assertEqual(len(list(r)), 0)
        r = c.search(
            "dc=python-ldap,dc=org",
            BASE, "(uid=tux)")
        self.assertEqual(len(list(r)), 0)

    def test_transaction_third_statement_fails(self):
        """
        Test success when 3rd statement fails;

        Need to roll back 2nd and 1st statements
        """
        c = tldap.connection
        c.add("uid=tux, ou=People, dc=python-ldap,dc=org", self.modlist)
        try:
            with tldap.transaction.commit_on_success():
                c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", {
                    "sn": (ldap3.MODIFY_REPLACE, "Milkshakes")})
                self.assertEqual(self.get(
                    c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'],
                    [b"Milkshakes"])
                c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", {
                    "sn": (ldap3.MODIFY_REPLACE, "Bannas")})
                self.assertEqual(self.get(
                    c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'],
                    [b"Bannas"])
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()
        except tldap.exceptions.TestFailure:
            pass
        else:
            self.fail("Exception not generated")
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'],
            [b"Torvalds"])

    def test_transaction_rename_rollback(self):
        """ Test rename with rollback. """
        c = tldap.connection
        onfailure = mock.Mock()
        c.add("uid=tux, ou=People, dc=python-ldap,dc=org", self.modlist)
        try:
            with tldap.transaction.commit_on_success():
                c.rename(
                    "uid=tux, ou=People, dc=python-ldap,dc=org", 'uid=tuz',
                    onfailure=onfailure)
                c.modify("uid=tuz, ou=People, dc=python-ldap,dc=org", {
                    "sn": (ldap3.MODIFY_REPLACE, "Tuz")})
                self.assert_dn_not_exists(
                    "uid=tux, ou=People, dc=python-ldap,dc=org")
                self.assert_dn_exists(
                    "uid=tuz, ou=People, dc=python-ldap,dc=org")
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()
        except tldap.exceptions.TestFailure:
            pass
        else:
            self.fail("Exception not generated")
        self.assert_dn_exists("uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assert_dn_not_exists("uid=tuz, ou=People, dc=python-ldap,dc=org")
        onfailure.assert_called_once_with()

    def test_transaction_rename_success(self):
        """ Test rename with success. """
        c = tldap.connection
        onfailure = mock.Mock()
        c.add("uid=tux, ou=People, dc=python-ldap,dc=org", self.modlist)
        with tldap.transaction.commit_on_success():
            c.rename(
                "uid=tux, ou=People, dc=python-ldap,dc=org", 'uid=tuz',
                onfailure=onfailure)
            c.modify("uid=tuz, ou=People, dc=python-ldap,dc=org", {
                'sn': (ldap3.MODIFY_REPLACE, "Tuz")})
            self.assert_dn_not_exists(
                "uid=tux, ou=People, dc=python-ldap,dc=org")
            self.assert_dn_exists(
                "uid=tuz, ou=People, dc=python-ldap,dc=org")
        self.assert_dn_not_exists("uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assert_dn_exists("uid=tuz, ou=People, dc=python-ldap,dc=org")
        onfailure.assert_not_called()

    def test_transaction_move_rollback(self):
        """ Test move with rollback. """
        c = tldap.connection
        onfailure = mock.Mock()
        c.add("uid=tux, ou=People, dc=python-ldap,dc=org", self.modlist)
        try:
            with tldap.transaction.commit_on_success():
                c.rename(
                    "uid=tux, ou=People, dc=python-ldap,dc=org",
                    "uid=tux", "ou=Groups, dc=python-ldap,dc=org",
                    onfailure=onfailure)
                self.assert_dn_not_exists(
                    "uid=tux, ou=People, dc=python-ldap,dc=org")
                self.assert_dn_exists(
                    "uid=tux, ou=Groups, dc=python-ldap,dc=org")
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()
        except tldap.exceptions.TestFailure:
            pass
        else:
            self.fail("Exception not generated")
        self.assert_dn_exists("uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assert_dn_not_exists("uid=tux, ou=Groups, dc=python-ldap,dc=org")
        onfailure.assert_called_once_with()

    def test_transaction_move_success(self):
        """ Test move with success. """
        c = tldap.connection
        onfailure = mock.Mock()
        c.add("uid=tux, ou=People, dc=python-ldap,dc=org", self.modlist)
        with tldap.transaction.commit_on_success():
            c.rename(
                "uid=tux, ou=People, dc=python-ldap,dc=org",
                "uid=tux", "ou=Groups, dc=python-ldap,dc=org",
                onfailure=onfailure)
            self.assert_dn_not_exists(
                "uid=tux, ou=People, dc=python-ldap,dc=org")
            self.assert_dn_exists(
                "uid=tux, ou=Groups, dc=python-ldap,dc=org")
        self.assert_dn_not_exists("uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assert_dn_exists("uid=tux, ou=Groups, dc=python-ldap,dc=org")
        onfailure.assert_not_called()

    def test_transaction_delete_and_add_rollback(self):
        """ Test roll back on error of delete and add of same user. """
        c = tldap.connection
        c.add("uid=tux, ou=People, dc=python-ldap,dc=org", self.modlist)
        try:
            with tldap.transaction.commit_on_success():
                c.delete("uid=tux, ou=People, dc=python-ldap,dc=org")
                self.assert_dn_not_exists(
                    "uid=tux, ou=People, dc=python-ldap,dc=org")
                c.add(
                    "uid=tux, ou=People, dc=python-ldap,dc=org", self.modlist)
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()
        except tldap.exceptions.TestFailure:
            pass
        else:
            self.fail("Exception not generated")
        self.assert_dn_exists("uid=tux, ou=People, dc=python-ldap,dc=org")

    def test_transaction_delete_and_add_success(self):
        """ Test delate and add same user. """
        c = tldap.connection
        c.add("uid=tux, ou=People, dc=python-ldap,dc=org", self.modlist)
        with tldap.transaction.commit_on_success():
            c.delete("uid=tux, ou=People, dc=python-ldap,dc=org")
            self.assert_dn_not_exists(
                "uid=tux, ou=People, dc=python-ldap,dc=org")
            c.add("uid=tux, ou=People, dc=python-ldap,dc=org", self.modlist)
        self.assert_dn_exists("uid=tux, ou=People, dc=python-ldap,dc=org")

    def test_transaction_delete_rollback(self):
        """ Test delete rollback. """
        c = tldap.connection
        onfailure = mock.Mock()
        c.add("uid=tux, ou=People, dc=python-ldap,dc=org", self.modlist)
        try:
            with tldap.transaction.commit_on_success():
                c.delete(
                    "uid=tux, ou=People, dc=python-ldap,dc=org",
                    onfailure=onfailure)
                self.assert_dn_not_exists(
                    "uid=tux, ou=People, dc=python-ldap,dc=org")
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()
        except tldap.exceptions.TestFailure:
            pass
        else:
            self.fail("Exception not generated")
        self.assert_dn_exists("uid=tux, ou=People, dc=python-ldap,dc=org")
        onfailure.assert_called_once_with()

    def test_transaction_delete_success(self):
        """ Test delete success. """
        c = tldap.connection
        onfailure = mock.Mock()
        c.add("uid=tux, ou=People, dc=python-ldap,dc=org", self.modlist)
        with tldap.transaction.commit_on_success():
            c.delete(
                "uid=tux, ou=People, dc=python-ldap,dc=org",
                onfailure=onfailure)
            self.assert_dn_not_exists(
                "uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assert_dn_not_exists(
            "uid=tux, ou=People, dc=python-ldap,dc=org")
        onfailure.assert_not_called()
        # FIXME: we should check all attributes are correct on restored object.
