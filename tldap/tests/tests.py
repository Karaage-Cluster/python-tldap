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

import six

import tldap
import tldap.schemas.rfc
import tldap.transaction
import tldap.exceptions
import tldap.modlist

import tldap.test.slapd
import tldap.tests.base as base
import tldap.tests.schemas as test_schemas

import ldap3
import ldap3.core.exceptions

server = None


NO_SUCH_OBJECT = ldap3.core.exceptions.LDAPNoSuchObjectResult


class BackendTest(base.LdapTestCase):
    def get(self, c, base):
        """
        returns ldap object for search_string
        raises MultipleResultsException if more than one
        entry exists for given search string
        """
        result_data = list(c.search(base, ldap3.SEARCH_SCOPE_BASE_OBJECT))
        no_results = len(result_data)
        self.assertEqual(no_results, 1)
        return result_data[0][1]

    def test_check_password(self):
        result = tldap.connection.check_password(
            'cn=Manager,dc=python-ldap,dc=org',
            'password'
        )
        self.assertEqual(result, True)
        result = tldap.connection.check_password(
            'cn=Manager,dc=python-ldap,dc=org',
            'password2'
        )
        self.assertEqual(result, False)

    def test_transactions(self):
        c = tldap.connection

        modlist = tldap.modlist.addModlist({
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

        c.add("ou=People, dc=python-ldap,dc=org", modlist)

        # test explicit roll back
        with tldap.transaction.commit_on_success():
            c.add("uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", {
                'sn': (ldap3.MODIFY_REPLACE, "Gates")})
            c.rollback()
        self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                          "uid=tux, ou=People, dc=python-ldap,dc=org")

        # test roll back on exception
        try:
            with tldap.transaction.commit_on_success():
                c.add("uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
                c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", {
                    'sn': (ldap3.MODIFY_REPLACE, "Gates")})
                raise RuntimeError("testing failure")
        except RuntimeError:
            pass
        self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                          "uid=tux, ou=People, dc=python-ldap,dc=org")

        # test success commits
        with tldap.transaction.commit_on_success():
            c.add("uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", {
                'sn': (ldap3.MODIFY_REPLACE, "Gates")})
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [b"Gates"])
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'],
            [b"000"])

        # test deleting attribute *of new object* with rollback
        try:
            with tldap.transaction.commit_on_success():
                c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", {
                    "telephoneNumber": (ldap3.MODIFY_DELETE, ['000'])})
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

        # test deleting attribute *of new object* with success
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", {
                "telephoneNumber": (ldap3.MODIFY_DELETE, [])})
            self.assertRaises(KeyError, lambda: self.get(
                c, "uid=tux, ou=People, dc=python-ldap,dc=org")[
                'telephoneNumber'])
        self.assertRaises(KeyError, lambda: self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'])

        # test adding attribute with rollback
        try:
            with tldap.transaction.commit_on_success():
                c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", {
                    "telephoneNumber": (ldap3.MODIFY_ADD, ["111"])})
                self.assertEqual(self.get(
                    c, "uid=tux, ou=People, dc=python-ldap,dc=org")[
                    'telephoneNumber'],
                    [b"111"])
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
        self.assertRaises(KeyError, lambda: self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'])

        # test adding attribute with success
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", {
                'telephoneNumber': (ldap3.MODIFY_ADD, ["111"])})
            self.assertEqual(self.get(
                c, "uid=tux, ou=People, dc=python-ldap,dc=org")[
                'telephoneNumber'], [b"111"])
            self.assertRaises(
                ldap3.core.exceptions.LDAPAttributeOrValueExistsResult,
                lambda: c.modify(
                    "uid=tux, ou=People, dc=python-ldap,dc=org", {
                        'telephoneNumber': (ldap3.MODIFY_ADD, ["111"])})
            )
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'],
            [b"111"])

        # test search scopes
        c.add("ou=Groups, dc=python-ldap,dc=org", {
            "objectClass": ["top", "organizationalunit"]
        })
        r = c.search(
            "uid=tux, ou=People, dc=python-ldap,dc=org",
            ldap3.SEARCH_SCOPE_BASE_OBJECT, "(uid=tux)")
        self.assertEqual(len(list(r)), 1)
        r = c.search(
            "ou=People, dc=python-ldap,dc=org",
            ldap3.SEARCH_SCOPE_BASE_OBJECT, "(uid=tux)")
        self.assertEqual(len(list(r)), 0)
        r = c.search(
            "dc=python-ldap,dc=org",
            ldap3.SEARCH_SCOPE_BASE_OBJECT, "(uid=tux)")
        self.assertEqual(len(list(r)), 0)
        r = c.search(
            "ou=Groups, dc=python-ldap,dc=org",
            ldap3.SEARCH_SCOPE_BASE_OBJECT, "(uid=tux)")
        self.assertEqual(len(list(r)), 0)
        r = c.search(
            "dc=python-ldap,dc=org",
            ldap3.SEARCH_SCOPE_BASE_OBJECT, "(uid=tux)")
        self.assertEqual(len(list(r)), 0)

        r = c.search(
            "uid=tux, ou=People, dc=python-ldap,dc=org",
            ldap3.SEARCH_SCOPE_SINGLE_LEVEL, "(uid=tux)")
        self.assertEqual(len(list(r)), 0)
        r = c.search(
            "ou=People, dc=python-ldap,dc=org",
            ldap3.SEARCH_SCOPE_SINGLE_LEVEL, "(uid=tux)")
        self.assertEqual(len(list(r)), 1)
        r = c.search(
            "dc=python-ldap,dc=org",
            ldap3.SEARCH_SCOPE_SINGLE_LEVEL, "(uid=tux)")
        self.assertEqual(len(list(r)), 0)
        r = c.search(
            "ou=Groups, dc=python-ldap,dc=org",
            ldap3.SEARCH_SCOPE_SINGLE_LEVEL, "(uid=tux)")
        self.assertEqual(len(list(r)), 0)
        r = c.search(
            "dc=python-ldap,dc=org",
            ldap3.SEARCH_SCOPE_BASE_OBJECT, "(uid=tux)")
        self.assertEqual(len(list(r)), 0)

        r = c.search(
            "uid=tux, ou=People, dc=python-ldap,dc=org",
            ldap3.SEARCH_SCOPE_WHOLE_SUBTREE, "(uid=tux)")
        self.assertEqual(len(list(r)), 1)
        r = c.search(
            "ou=People, dc=python-ldap,dc=org",
            ldap3.SEARCH_SCOPE_WHOLE_SUBTREE, "(uid=tux)")
        self.assertEqual(len(list(r)), 1)
        r = c.search(
            "dc=python-ldap,dc=org",
            ldap3.SEARCH_SCOPE_WHOLE_SUBTREE, "(uid=tux)")
        self.assertEqual(len(list(r)), 1)
        r = c.search(
            "ou=Groups, dc=python-ldap,dc=org",
            ldap3.SEARCH_SCOPE_WHOLE_SUBTREE, "(uid=tux)")
        self.assertEqual(len(list(r)), 0)
        r = c.search(
            "dc=python-ldap,dc=org",
            ldap3.SEARCH_SCOPE_BASE_OBJECT, "(uid=tux)")
        self.assertEqual(len(list(r)), 0)

        # test replacing attribute with rollback
        try:
            with tldap.transaction.commit_on_success():
                c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", {
                    "telephoneNumber": (ldap3.MODIFY_REPLACE, ["222"])})
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
            [b"111"])

        # test replacing attribute with success
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", {
                'telephoneNumber': (ldap3.MODIFY_REPLACE, "222")})
            self.assertEqual(self.get(
                c, "uid=tux, ou=People, dc=python-ldap,dc=org")[
                'telephoneNumber'],
                [b"222"])
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'],
            [b"222"])

        # test deleting attribute value with rollback
        try:
            with tldap.transaction.commit_on_success():
                c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", {
                    "telephoneNumber": (ldap3.MODIFY_DELETE, "222")})
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
            [b"222"])

        # test deleting attribute value with success
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", {
                "telephoneNumber": (ldap3.MODIFY_DELETE, "222")})
            self.assertRaises(KeyError, lambda: self.get(
                c,
                "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber']
            )
        self.assertRaises(KeyError, lambda: self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'])

        # test success when 3rd statement fails; need to roll back 2nd and 1st
        # statements
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
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [b"Gates"])

        # test rename with rollback
        try:
            with tldap.transaction.commit_on_success():
                c.rename(
                    "uid=tux, ou=People, dc=python-ldap,dc=org", 'uid=tuz')
                c.modify("uid=tuz, ou=People, dc=python-ldap,dc=org", {
                    "sn": (ldap3.MODIFY_REPLACE, "Tuz")})
                self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                                  "uid=tux, ou=People, dc=python-ldap,dc=org")
                self.assertEqual(self.get(
                    c, "uid=tuz, ou=People, dc=python-ldap,dc=org")['sn'],
                    [b"Tuz"])
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()
        except tldap.exceptions.TestFailure:
            pass
        else:
            self.fail("Exception not generated")
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [b"Gates"])
        self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                          "uid=tuz, ou=People, dc=python-ldap,dc=org")

        # test rename with success
        with tldap.transaction.commit_on_success():
            c.rename("uid=tux, ou=People, dc=python-ldap,dc=org", 'uid=tuz')
            c.modify("uid=tuz, ou=People, dc=python-ldap,dc=org", {
                'sn': (ldap3.MODIFY_REPLACE, "Tuz")})
            self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                              "uid=tux, ou=People, dc=python-ldap,dc=org")
            self.assertEqual(self.get(
                c, "uid=tuz, ou=People, dc=python-ldap,dc=org")['sn'],
                [b"Tuz"])
        self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                          "uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(self.get(
            c, "uid=tuz, ou=People, dc=python-ldap,dc=org")['sn'], [b"Tuz"])

        # test rename back with success
        with tldap.transaction.commit_on_success():
            c.modify("uid=tuz, ou=People, dc=python-ldap,dc=org", {
                'sn': (ldap3.MODIFY_REPLACE, "Gates")})
            c.rename("uid=tuz, ou=People, dc=python-ldap,dc=org", 'uid=tux')
            self.assertEqual(self.get(
                c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'],
                [b"Gates"])
            self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                              "uid=tuz, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [b"Gates"])
        self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                          "uid=tuz, ou=People, dc=python-ldap,dc=org")

        # test rename with success
        with tldap.transaction.commit_on_success():
            c.rename("uid=tux, ou=People, dc=python-ldap,dc=org", 'cn=tux')
            c.modify("cn=tux, ou=People, dc=python-ldap,dc=org", {
                'sn': (ldap3.MODIFY_REPLACE, "Tuz")})
            self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                              "uid=tux, ou=People, dc=python-ldap,dc=org")
            self.assertEqual(self.get(
                c, "cn=tux, ou=People, dc=python-ldap,dc=org")['sn'], [b"Tuz"])
        self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                          "uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(self.get(
            c, "cn=tux, ou=People, dc=python-ldap,dc=org")['sn'], [b"Tuz"])

        # test rename back with success
        with tldap.transaction.commit_on_success():
            c.modify("cn=tux, ou=People, dc=python-ldap,dc=org", {
                'sn': (ldap3.MODIFY_REPLACE, "Gates")})
            c.rename("cn=tux, ou=People, dc=python-ldap,dc=org", 'uid=tux')
            self.assertEqual(self.get(
                c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'],
                [b"Gates"])
            self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                              "cn=tux, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [b"Gates"])
        self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                          "cn=tux, ou=People, dc=python-ldap,dc=org")

        # test rename with success
        with tldap.transaction.commit_on_success():
            c.rename("uid=tux, ou=People, dc=python-ldap,dc=org",
                     'cn=Tux Torvalds')
            c.modify("cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org", {
                'sn': (ldap3.MODIFY_REPLACE, "Tuz")})
            self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                              "uid=tux, ou=People, dc=python-ldap,dc=org")
            self.assertEqual(self.get(
                c, "cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org")['sn'],
                [b"Tuz"])
        self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                          "uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(self.get(
            c, "cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org")['sn'],
            [b"Tuz"])

        # test rename back with success
        with tldap.transaction.commit_on_success():
            c.modify("cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org", {
                'sn': (ldap3.MODIFY_REPLACE, "Gates")})
            c.modify("cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org", {
                "cn": (ldap3.MODIFY_ADD, ["meow"])})
            c.rename(
                "cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org", 'uid=tux')
            c.modify("uid=Tux, ou=People, dc=python-ldap,dc=org", {
                "cn": (ldap3.MODIFY_REPLACE, "Tux Torvalds")})
            self.assertEqual(self.get(
                c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'],
                [b"Gates"])
            self.assertEqual(self.get(
                c, "uid=tux, ou=People, dc=python-ldap,dc=org")['cn'],
                [b"Tux Torvalds"])
            self.assertRaises(
                NO_SUCH_OBJECT, self.get, c,
                "cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [b"Gates"])
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['cn'],
            [b"Tux Torvalds"])
        self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                          "cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org")

        # test move with rollback
        self.get(c, "ou=People, dc=python-ldap,dc=org")
        self.get(c, "ou=Groups, dc=python-ldap,dc=org")
        self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                          "uid=tux, ou=Group, dc=python-ldap,dc=org")
        try:
            with tldap.transaction.commit_on_success():
                c.rename(
                    "uid=tux, ou=People, dc=python-ldap,dc=org",
                    "uid=tux", "ou=Groups, dc=python-ldap,dc=org")
                self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                                  "uid=tux, ou=People, dc=python-ldap,dc=org")
                self.get(c, "uid=tux, ou=Groups, dc=python-ldap,dc=org")
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()
        except tldap.exceptions.TestFailure:
            pass
        else:
            self.fail("Exception not generated")
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [b"Gates"])
        self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                          "uid=tux, ou=Groups, dc=python-ldap,dc=org")

        # test move with success
        self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")
        with tldap.transaction.commit_on_success():
            c.rename(
                "uid=tux, ou=People, dc=python-ldap,dc=org",
                "uid=tux", "ou=Groups, dc=python-ldap,dc=org")
            self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                              "uid=tux, ou=People, dc=python-ldap,dc=org")
            self.get(c, "uid=tux, ou=Groups, dc=python-ldap,dc=org")
        self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                          "uid=tux, ou=People, dc=python-ldap,dc=org")
        self.get(c, "uid=tux, ou=Groups, dc=python-ldap,dc=org")

        # test move back
        with tldap.transaction.commit_on_success():
            c.rename(
                "uid=tux, ou=Groups, dc=python-ldap,dc=org",
                "uid=tux", "ou=People, dc=python-ldap,dc=org")
            self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")
            self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                              "uid=tux, ou=Groups, dc=python-ldap,dc=org")
        self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                          "uid=tux, ou=Groups, dc=python-ldap,dc=org")

        # test roll back on error of delete and add of same user
        try:
            with tldap.transaction.commit_on_success():
                c.delete("uid=tux, ou=People, dc=python-ldap,dc=org")
                self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                                  "uid=tux, ou=People, dc=python-ldap,dc=org")
#                c.add("uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()
        except tldap.exceptions.TestFailure:
            pass
        else:
            self.fail("Exception not generated")
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [b"Gates"])

        # test delate and add same user
        with tldap.transaction.commit_on_success():
            c.delete("uid=tux, ou=People, dc=python-ldap,dc=org")
            self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                              "uid=tux, ou=People, dc=python-ldap,dc=org")
            c.add("uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'],
            [b"Torvalds"])

        # test delate
        with tldap.transaction.commit_on_success():
            c.delete("uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assertRaises(NO_SUCH_OBJECT, self.get, c,
                          "uid=tux, ou=People, dc=python-ldap,dc=org")


class ModelTest(base.LdapTestCase):
    def test_transactions(self):
        organizationalUnit = tldap.schemas.rfc.organizationalUnit
        organizationalUnit.objects.create(
            dn="ou=People, dc=python-ldap,dc=org")
        organizationalUnit.objects.create(
            dn="ou=Groups, dc=python-ldap,dc=org")

        c = tldap.connection

        person = test_schemas.person
        DoesNotExist = person.DoesNotExist
        AlreadyExists = person.AlreadyExists
        get = person.objects.get
        get_or_create = person.objects.get_or_create
        create = person.objects.create

        kwargs = {
            'givenName': "Tux",
            'sn': "Torvalds",
            'cn': "Tux Torvalds",
            'telephoneNumber': "000",
            'mail': "tuz@example.org",
            'o': "Linux Rules",
            'userPassword': "silly",
        }

        # test explicit roll back
        with tldap.transaction.commit_on_success():
            p = create(uid="tux", **kwargs)
            p.sn = "Gates"
            p.save()
            c.rollback()
        self.assertRaises(DoesNotExist, get, uid="tux")

        # test roll back on exception
        try:
            with tldap.transaction.commit_on_success():
                p = create(uid="tux", **kwargs)
                p.sn = "Gates"
                p.save()
                raise RuntimeError("testing failure")
        except RuntimeError:
            pass
        self.assertRaises(DoesNotExist, get, uid="tux")

        # test success commits
        with tldap.transaction.commit_on_success():
            p = create(uid="tux", **kwargs)
            p.sn = "Gates"
            p.save()
        self.assertEqual(get(uid="tux").sn, "Gates")
        self.assertEqual(get(uid="tux").telephoneNumber, "000")

        # test deleting attribute
        p, created = get_or_create(uid="tux")
        self.assertEqual(created, False)
        p.telephoneNumber = None

        # test deleting attribute *of new object* with rollback
        try:
            with tldap.transaction.commit_on_success():
                p.save()
                self.assertEqual(get(uid="tux").telephoneNumber, None)
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()
        except tldap.exceptions.TestFailure:
            pass
        else:
            self.fail("Exception not generated")
        self.assertEqual(get(uid="tux").telephoneNumber, "000")

        # test deleting attribute *of new object* with success
        with tldap.transaction.commit_on_success():
            p.save()
            self.assertEqual(get(uid="tux").telephoneNumber, None)
        self.assertEqual(get(uid="tux").telephoneNumber, None)

        # test adding attribute
        p, created = get_or_create(uid="tux")
        self.assertEqual(created, False)
        p.telephoneNumber = "111"

        # test adding attribute with rollback
        try:
            with tldap.transaction.commit_on_success():
                p.save()
                self.assertEqual(get(uid="tux").telephoneNumber, "111")
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()
        except tldap.exceptions.TestFailure:
            pass
        else:
            self.fail("Exception not generated")
        self.assertEqual(get(uid="tux").telephoneNumber, None)

        # test adding attribute with success
        with tldap.transaction.commit_on_success():
            p.save()
            self.assertEqual(get(uid="tux").telephoneNumber, "111")
        self.assertEqual(get(uid="tux").telephoneNumber, "111")

        # test replacing attribute
        p, created = get_or_create(uid="tux")
        self.assertEqual(created, False)
        p.telephoneNumber = "222"

        # test replacing attribute with rollback
        try:
            with tldap.transaction.commit_on_success():
                p.save()
                self.assertEqual(get(uid="tux").telephoneNumber, "222")
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()
        except tldap.exceptions.TestFailure:
            pass
        else:
            self.fail("Exception not generated")
        self.assertEqual(get(uid="tux").telephoneNumber, "111")

        # test replacing attribute with success
        with tldap.transaction.commit_on_success():
            p.save()
            self.assertEqual(get(uid="tux").telephoneNumber, "222")
        self.assertEqual(get(uid="tux").telephoneNumber, "222")

        # test deleting attribute
        p, created = get_or_create(uid="tux")
        self.assertEqual(created, False)
        p.telephoneNumber = None

        # test deleting attribute *of new object* with rollback
        try:
            with tldap.transaction.commit_on_success():
                p.save()
                self.assertEqual(get(uid="tux").telephoneNumber, None)
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()
        except tldap.exceptions.TestFailure:
            pass
        else:
            self.fail("Exception not generated")
        self.assertEqual(get(uid="tux").telephoneNumber, "222")

        # test deleting attribute *of new object* with success
        with tldap.transaction.commit_on_success():
            p.save()
            self.assertEqual(get(uid="tux").telephoneNumber, None)
        self.assertEqual(get(uid="tux").telephoneNumber, None)

        # test success when 3rd statement fails; need to roll back 2nd and 1st
        # statements
        try:
            with tldap.transaction.commit_on_success():
                p = get(uid="tux")
                p.sn = "Milkshakes"
                p.save()
                self.assertEqual(get(uid="tux").sn, "Milkshakes")

                p.sn = "Bannas"
                p.save()
                self.assertEqual(get(uid="tux").sn, "Bannas")

                self.assertRaises(AlreadyExists,
                                  lambda: p.save(force_add=True))
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()
        except tldap.exceptions.TestFailure:
            pass
        else:
            self.fail("Exception not generated")
        self.assertEqual(get(uid="tux").sn, "Gates")

        # test delate and add same user
        with tldap.transaction.commit_on_success():
            p = get(uid="tux")
            p.delete()
            self.assertRaises(DoesNotExist, get, uid="tux")
            p.save()
            self.assertEqual(get(uid="tux").sn, "Gates")
        self.assertEqual(get(uid="tux").sn, "Gates")

        # test rename with rollback
        try:
            with tldap.transaction.commit_on_success():
                p = get(uid="tux")
                p.rename(uid='tuz')
                p.sn = "Tuz"
                p.save()
                self.assertRaises(DoesNotExist, get, uid="tux")
                self.assertEqual(get(uid="tuz").sn, "Tuz")
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()
        except tldap.exceptions.TestFailure:
            pass
        else:
            self.fail("Exception not generated")
        self.assertEqual(get(uid="tux").sn, "Gates")
        self.assertRaises(DoesNotExist, get, uid="tuz")

        # test rename with success
        with tldap.transaction.commit_on_success():
            p = get(uid="tux")
            p.rename(uid='tuz')
            p.sn = "Tuz"
            p.save()
            self.assertRaises(DoesNotExist, get, uid="tux")
            self.assertEqual(get(uid="tuz").sn, "Tuz")
        self.assertRaises(DoesNotExist, get, uid="tux")
        self.assertEqual(get(uid="tuz").sn, "Tuz")

        # test rename back with success
        with tldap.transaction.commit_on_success():
            p = get(uid="tuz")
            p.rename(uid='tux')
            p.sn = "Gates"
            p.save()
            self.assertEqual(get(uid="tux").sn, "Gates")
            self.assertRaises(DoesNotExist, get, uid="tuz")
        self.assertEqual(get(uid="tux").sn, "Gates")
        self.assertRaises(DoesNotExist, get, uid="tuz")

        # test move with rollback
        try:
            with tldap.transaction.commit_on_success():
                p = get(uid="tux")
                p.rename("ou=Groups, dc=python-ldap,dc=org")
                self.assertRaises(DoesNotExist, get, uid="tux")
                c = tldap.connection
                groups = person.objects.base_dn(
                    "ou=Groups, dc=python-ldap,dc=org")
                groups.get(uid="tux")
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()
        except tldap.exceptions.TestFailure:
            pass
        else:
            self.fail("Exception not generated")
        self.assertEqual(get(uid="tux").sn, "Gates")
        groups = person.objects.base_dn("ou=Groups, dc=python-ldap,dc=org")
        self.assertRaises(DoesNotExist, groups.get, uid="tux")

        # test move with success
        with tldap.transaction.commit_on_success():
            p = get(uid="tux")
            p.rename("ou=Groups, dc=python-ldap,dc=org")
            self.assertRaises(DoesNotExist, get, uid="tux")
            groups = person.objects.base_dn("ou=Groups, dc=python-ldap,dc=org")
            groups.get(uid="tux")
        self.assertRaises(DoesNotExist, get, uid="tux")
        groups = person.objects.base_dn("ou=Groups, dc=python-ldap,dc=org")
        groups.get(uid="tux")

        # test move back with success
        with tldap.transaction.commit_on_success():
            groups = person.objects.base_dn("ou=Groups, dc=python-ldap,dc=org")
            p = groups.get(uid="tux")
            p.rename("ou=People, dc=python-ldap,dc=org")
            self.assertEqual(get(uid="tux").sn, "Gates")
            groups = person.objects.base_dn("ou=Groups, dc=python-ldap,dc=org")
            self.assertRaises(DoesNotExist, groups.get, uid="tux")
        self.assertEqual(get(uid="tux").sn, "Gates")
        groups = person.objects.base_dn("ou=Groups, dc=python-ldap,dc=org")
        self.assertRaises(DoesNotExist, groups.get, uid="tux")

        # hack for testing
        for i in p._meta.fields:
            if i.name == "cn":
                i._max_instances = 2

        # test rename with success
        with tldap.transaction.commit_on_success():
            p = get(uid="tux")
            p.rename(cn='tux')
            self.assertEqual(p.cn, ["Tux Torvalds", "tux"])

        with tldap.transaction.commit_on_success():
            p.sn = "Tuz"
            p.save()
            self.assertRaises(DoesNotExist, get, uid="tux")
            self.assertEqual(
                get(dn="cn=tux, ou=People, dc=python-ldap,dc=org").sn, "Tuz")
            self.assertEqual(
                get(dn="cn=tux, ou=People, dc=python-ldap,dc=org").uid, None)
            self.assertEqual(
                get(dn="cn=tux, ou=People, dc=python-ldap,dc=org").cn,
                ["Tux Torvalds", "tux"])
        self.assertRaises(DoesNotExist, get, uid="tux")
        self.assertEqual(
            get(dn="cn=tux, ou=People, dc=python-ldap,dc=org").sn, "Tuz")
        self.assertEqual(
            get(dn="cn=tux, ou=People, dc=python-ldap,dc=org").uid, None)
        self.assertEqual(get(dn="cn=tux, ou=People, dc=python-ldap,dc=org")
                         .cn, ["Tux Torvalds", "tux"])

        # test rename back with success
        with tldap.transaction.commit_on_success():
            p = get(dn="cn=tux, ou=People, dc=python-ldap,dc=org")
            p.rename(uid='tux')
            self.assertEqual(p.cn, ["Tux Torvalds"])

        with tldap.transaction.commit_on_success():
            p.sn = "Gates"
            p.save()
            self.assertEqual(get(uid="tux").sn, "Gates")
            self.assertRaises(DoesNotExist, get,
                              dn="cn=tux, ou=People, dc=python-ldap,dc=org")
            self.assertEqual(get(uid="tux").uid, "tux")
            self.assertEqual(get(uid="tux").cn, ["Tux Torvalds"])
        self.assertEqual(get(uid="tux").sn, "Gates")
        self.assertRaises(
            DoesNotExist, get, dn="cn=tux, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(get(uid="tux").uid, "tux")
        self.assertEqual(get(uid="tux").cn, ["Tux Torvalds"])

        # test rename with success
        with tldap.transaction.commit_on_success():
            p = get(uid="tux")
            p.rename(cn='Tux Torvalds')
            self.assertEqual(p.cn, ["Tux Torvalds"])

        with tldap.transaction.commit_on_success():
            p.sn = "Tuz"
            p.save()
            self.assertRaises(DoesNotExist, get, uid="tux")
            self.assertEqual(get(
                dn="cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org").sn,
                "Tuz")
            self.assertEqual(get(
                dn="cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org").uid,
                None)
            self.assertEqual(get(
                dn="cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org").cn,
                ["Tux Torvalds"])
        self.assertRaises(DoesNotExist, get, uid="tux")
        self.assertEqual(get(
            dn="cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org").sn, "Tuz")
        self.assertEqual(get(
            dn="cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org").uid, None)
        self.assertEqual(get(
            dn="cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org").cn,
            ["Tux Torvalds"])

        # test rename back with success
        with tldap.transaction.commit_on_success():
            p = get(dn="cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org")
            p.cn = ['sss', 'Tux Torvalds']
            p.save()
            p.rename(uid='tux')
            self.assertEqual(p.cn, ["sss"])

        with tldap.transaction.commit_on_success():
            p.sn = "Gates"
            p.cn = ['Tux Torvalds']
            p.save()
            self.assertEqual(get(uid="tux").sn, "Gates")
            self.assertRaises(
                DoesNotExist, get,
                dn="cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org")
            self.assertEqual(get(uid="tux").uid, "tux")
            self.assertEqual(get(uid="tux").cn, ["Tux Torvalds"])
        self.assertEqual(get(uid="tux").sn, "Gates")
        self.assertRaises(
            DoesNotExist, get,
            dn="cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(get(uid="tux").uid, "tux")
        self.assertEqual(get(uid="tux").cn, ["Tux Torvalds"])

        # unhack for testing
        for i in p._meta.fields:
            if i.name == "cn":
                i._max_instances = 1

        # test roll back on error of delete and add of same user
        old_p = p
        try:
            with tldap.transaction.commit_on_success():
                p.delete()
                self.assertRaises(DoesNotExist, get, uid="tux")
                p = create(uid="tux", **kwargs)
                self.assertRaises(AlreadyExists, create, uid="tux", **kwargs)
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()
        except tldap.exceptions.TestFailure:
            pass
        else:
            self.fail("Exception not generated")
        self.assertEqual(get(uid="tux").sn, "Gates")

        # test delate
        with tldap.transaction.commit_on_success():
            old_p.delete()
        self.assertRaises(DoesNotExist, get, uid="tux")

        return

    def test_query(self):
        organizationalUnit = tldap.schemas.rfc.organizationalUnit
        organizationalUnit.objects.create(
            dn="ou=People, dc=python-ldap,dc=org", ou="People")

        organizationalUnit = tldap.schemas.rfc.organizationalUnit
        organizationalUnit.objects.create(
            dn="ou=Group, dc=python-ldap,dc=org", ou="Group")

        person = test_schemas.person
        group = test_schemas.group

        kwargs = {
            'givenName': "Tux",
            'sn': "Torvalds",
            'cn': "Tux Torvalds",
            'telephoneNumber': "000",
            'mail': "tuz@example.org",
            'o': six.u("Linux Rules £"),
            'userPassword': "silly",
        }
        p1 = person.objects.create(uid="tux", **kwargs)
        p2 = person.objects.create(uid="tuz", **kwargs)

        p = person.objects.get(dn="uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(p.o, six.u("Linux Rules £"))

        g1 = group.objects.create(cn="group1", gidNumber=10, memberUid=["tux"])
        g2 = group.objects.create(
            cn="group2", gidNumber=11, memberUid=["tux", "tuz"])

        self.assertEqual(
            person.objects.all()._get_filter(tldap.Q(uid='t\\ux')),
            "(uid=t\\5cux)")
        self.assertEqual(
            person.objects.all()._get_filter(~tldap.Q(uid='tux')),
            "(!(uid=tux))")
        self.assertEqual(
            person.objects.all(
            )._get_filter(tldap.Q(uid='tux') | tldap.Q(uid='tuz')),
            "(|(uid=tux)(uid=tuz))")
        self.assertEqual(
            person.objects.all(
            )._get_filter(tldap.Q() | tldap.Q(uid='tux') | tldap.Q(uid='tuz')),
            "(|(uid=tux)(uid=tuz))")
        self.assertEqual(
            person.objects.all(
            )._get_filter(tldap.Q() & tldap.Q(uid='tux') & tldap.Q(uid='tuz')),
            "(&(uid=tux)(uid=tuz))")
        self.assertEqual(
            person.objects.all()._get_filter(tldap.Q(
                uid='tux') & (tldap.Q(uid='tuz') | tldap.Q(uid='meow'))),
            "(&(uid=tux)(|(uid=tuz)(uid=meow)))")

        person.objects.get(dn="uid=tux,ou=People, dc=python-ldap,dc=org")
        self.assertRaises(person.DoesNotExist, person.objects.get,
                          dn="uid=tuy,ou=People, dc=python-ldap,dc=org")
        person.objects.get(dn="uid=tuz,ou=People, dc=python-ldap,dc=org")

        r = person.objects.filter(
            tldap.Q(dn="uid=tux,ou=People, dc=python-ldap,dc=org") |
            tldap.Q(dn="uid=tuy,ou=People, dc=python-ldap,dc=org") |
            tldap.Q(dn="uid=tuz,ou=People, dc=python-ldap,dc=org"))
        self.assertEqual(len(r), 2)

        r = person.objects.filter(tldap.Q(uid='tux') | tldap.Q(uid='tuz'))
        self.assertEqual(len(r), 2)

        self.assertRaises(person.MultipleObjectsReturned, person.objects.get,
                          tldap.Q(uid='tux') | tldap.Q(uid='tuz'))
        person.objects.get(~tldap.Q(uid='tuz'))

        r = g1.secondary_people.all()
        self.assertEqual(len(r), 1)

        r = g2.secondary_people.all()
        self.assertEqual(len(r), 2)

        r = p1.secondary_groups.all()
        self.assertEqual(len(r), 2)

        r = p2.secondary_groups.all()
        self.assertEqual(len(r), 1)

        p1.secondary_groups.create(cn="drwho", gidNumber=12)

        o, c = p1.secondary_groups.get_or_create(
            cn="startrek", defaults={'gidNumber': 13})
        self.assertEqual(c, True)

        o, c = p1.secondary_groups.get_or_create(
            cn="startrek", defaults={'gidNumber': 13})
        self.assertEqual(c, False)

        g1.secondary_people.create(
            uid="dalek", sn="Exterminate", cn="You will be Exterminated!")
        self.assertEqual(g1.memberUid, ['tux', 'dalek'])

        o, c = g1.secondary_people.get_or_create(
            uid="dalek_leader", sn="Exterminate",
            defaults={'cn': "You will be Exterminated!"})
        self.assertEqual(c, True)
        self.assertEqual(g1.memberUid, ['tux', 'dalek', 'dalek_leader'])

        o, c = g1.secondary_people.get_or_create(
            uid="dalek_leader", sn="Exterminate",
            defaults={'cn': "You will be Exterminated!"})
        self.assertEqual(c, False)
        self.assertEqual(g1.memberUid, ['tux', 'dalek', 'dalek_leader'])

        r = g1.secondary_people.all()
        self.assertEqual(len(r), 3)

        r = g2.secondary_people.all()
        self.assertEqual(len(r), 2)

        r = p1.secondary_groups.all()
        self.assertEqual(len(r), 4)

        r = p2.secondary_groups.all()
        self.assertEqual(len(r), 1)

        u = g1.primary_accounts.create(
            uid="cyberman", sn="Deleted", cn="You will be Deleted!",
            uidNumber=100, homeDirectory="/tmp")

        r = g1.primary_accounts.all()
        self.assertEqual(len(r), 1)

        group = r[0].primary_group.get()
        self.assertEqual(group, g1)
        self.assertEqual(group.memberUid, g1.memberUid)

        group.primary_accounts.add(u)
        self.assertRaises(tldap.exceptions.ValidationError,
                          group.primary_accounts.remove, u)

        r = group.secondary_people.all()
        self.assertEqual(len(r), 3)

        group.secondary_people.clear()

        r = group.secondary_people.all()
        self.assertEqual(len(r), 0)

        group.secondary_people.add(p1)

        r = group.secondary_people.all()
        self.assertEqual(len(r), 1)

        group.secondary_people.remove(p1)

        r = group.secondary_people.all()
        self.assertEqual(len(r), 0)

        u.secondary_groups.add(group)

        r = group.secondary_people.all()
        self.assertEqual(len(r), 1)

        u.secondary_groups.remove(group)

        r = group.secondary_people.all()
        self.assertEqual(len(r), 0)

        u.primary_group = g2
        u.save()

        r = g2.primary_accounts.all()
        self.assertEqual(len(list(r)), 1)

        u.primary_group = None
        self.assertRaises(tldap.exceptions.ValidationError, u.save)

        u1 = person.objects.get(dn="uid=tux,ou=People, dc=python-ldap,dc=org")
        u2 = person.objects.get(dn="uid=tuz,ou=People, dc=python-ldap,dc=org")

        u2.managed_by = u1
        u2.save()
        self.assertEqual(u2.managed_by.get_obj(), u1)
        r = u1.manager_of.all()
        self.assertEqual(len(list(r)), 1)
        r = person.objects.filter(managed_by=u1)
        self.assertEqual(len(list(r)), 1)
        r = person.objects.filter(manager_of=u2)
        self.assertEqual(len(list(r)), 1)

        u1.manager_of.remove(u2)
        self.assertEqual(u2.managed_by.get_obj(), None)
        r = u1.manager_of.all()
        self.assertEqual(len(list(r)), 0)

        u1.manager_of.add(u2)
        self.assertEqual(u2.managed_by.get_obj(), u1)
        r = u1.manager_of.all()
        self.assertEqual(len(list(r)), 1)


class UserAPITest(base.LdapTestCase):
    def setUp(self):
        super(UserAPITest, self).setUp()

        organizationalUnit = tldap.schemas.rfc.organizationalUnit
        organizationalUnit.objects.create(
            dn="ou=People, dc=python-ldap,dc=org", ou="People")

        organizationalUnit = tldap.schemas.rfc.organizationalUnit
        organizationalUnit.objects.create(
            dn="ou=Group, dc=python-ldap,dc=org", ou="Group")

        self.account = test_schemas.account
        self.group = test_schemas.group

        account = self.account
        group = self.group

        u1 = account.objects.create(
            uid="testuser1", uidNumber=1000, gidNumber=10001,
            homeDirectory="/tmp", sn='User',
            mail="t.user1@example.com",
            cn="Test User 1")

        u2 = account.objects.create(
            uid="testuser2", uidNumber=1001, gidNumber=10001,
            homeDirectory="/tmp", sn='User',
            mail="t.user2@example.com",
            cn="Test User 2")

        u3 = account.objects.create(
            uid="testuser3", uidNumber=1002, gidNumber=10001,
            homeDirectory="/tmp", sn='User',
            mail="t.user3@example.com",
            cn="Test User 3")

        g1 = group.objects.create(
            cn="systems", gidNumber=10001,
        )
        g1.secondary_accounts = [u1]

        g2 = group.objects.create(
            cn="empty", gidNumber=10002,
            description="Empty Group",
        )
        g2.secondary_accounts = []

        g3 = group.objects.create(
            cn="full", gidNumber=10003,
        )
        g3.secondary_accounts = [u1, u2, u3]

    def test_get_users(self):
        self.assertEqual(len(self.account.objects.all()), 3)

    def test_get_user(self):
        u = self.account.objects.get(uid='testuser3')
        self.assertEqual(u.mail, 't.user3@example.com')

    def test_delete_user(self):
        self.assertEqual(len(self.account.objects.all()), 3)
        u = self.account.objects.get(uid='testuser2')
        u.delete()
        self.assertEqual(len(self.account.objects.all()), 2)

    def test_in_ldap(self):
        self.account.objects.get(uid='testuser1')
        self.assertRaises(self.account.DoesNotExist,
                          self.account.objects.get, cn='testuser4')

    def test_update_user(self):
        u = self.account.objects.get(uid='testuser1')
        self.assertEqual(u.sn, 'User')
        u.sn = "Bloggs"
        u.save()
        u = self.account.objects.get(uid='testuser1')
        self.assertEqual(u.sn, 'Bloggs')

    def test_update_user_no_modifications(self):
        u = self.account.objects.get(uid='testuser1')
        self.assertEqual(u.sn, 'User')
        u.sn = "User"
        u.save()
        u = self.account.objects.get(uid='testuser1')
        self.assertEqual(u.sn, 'User')

#    def test_lock_unlock(self):
#        u = self.account.objects.get(uid='testuser1')
#        u.unlock()
#        u.save()
#
#        u = self.account.objects.get(uid='testuser1')
#        self.assertEqual(u.is_locked(), False)
#        u.lock()
#        u.save()
#
#        u = self.account.objects.get(uid='testuser1')
#        self.assertEqual(u.is_locked(), True)
#
#        u.unlock()
#        u.save()
#        self.assertEqual(u.is_locked(), False)

    def test_user_slice(self):
        self.account.objects.get(uid='testuser1').save()
        users = self.account.objects.filter(
            tldap.Q(cn__contains='nothing') | tldap.Q(cn__contains="user"))
        self.assertEqual(users[0].uid, "testuser1")
        self.assertEqual(users[1].uid, "testuser2")
        self.assertEqual(users[2].uid, "testuser3")
        self.assertRaises(IndexError, users.__getitem__, 3)
        a = iter(users[1:4])
        self.assertEqual(next(a).uid, "testuser2")
        self.assertEqual(next(a).uid, "testuser3")
        self.assertRaises(StopIteration, lambda: next(a))

    def test_user_search(self):
        self.account.objects.get(uid='testuser1').save()
        users = self.account.objects.filter(cn__contains='User')
        self.assertEqual(len(users), 3)

    def test_user_search_one(self):
        self.account.objects.get(uid='testuser1').save()
        users = self.account.objects.filter(uid__contains='testuser1')
        self.assertEqual(len(users), 1)

    def test_user_search_empty(self):
        self.account.objects.get(uid='testuser1').save()
        users = self.account.objects.filter(cn__contains='nothing')
        self.assertEqual(len(users), 0)

    def test_user_search_multi(self):
        self.account.objects.get(uid='testuser1').save()
        users = self.account.objects.filter(
            tldap.Q(cn__contains='nothing') | tldap.Q(cn__contains="user"))
        self.assertEqual(len(users), 3)

    def test_get_groups_empty(self):
        u = self.account.objects.get(uid="testuser2")
        u.secondary_groups.clear()
        groups = u.secondary_groups.all()
        self.assertEqual(len(groups), 0)
        groups = self.group.objects.filter(secondary_accounts=u)
        self.assertEqual(len(groups), 0)

    def test_get_groups_one(self):
        u = self.account.objects.get(uid="testuser2")
        groups = u.secondary_groups.all()
        self.assertEqual(len(groups), 1)
        groups = self.group.objects.filter(secondary_accounts=u)
        self.assertEqual(len(groups), 1)

    def test_get_groups_many(self):
        u = self.account.objects.get(uid="testuser1")
        groups = u.secondary_groups.all()
        self.assertEqual(len(groups), 2)
        groups = self.group.objects.filter(secondary_accounts=u)
        self.assertEqual(len(groups), 2)


class GroupAPITest(base.LdapTestCase):
    def setUp(self):
        super(GroupAPITest, self).setUp()

        organizationalUnit = tldap.schemas.rfc.organizationalUnit
        organizationalUnit.objects.create(
            dn="ou=People, dc=python-ldap,dc=org", ou="People")

        organizationalUnit = tldap.schemas.rfc.organizationalUnit
        organizationalUnit.objects.create(
            dn="ou=Group, dc=python-ldap,dc=org", ou="Group")

        self.account = test_schemas.account
        self.group = test_schemas.group

        account = self.account
        group = self.group

        u1 = account.objects.create(
            uid="testuser1", uidNumber=1000, gidNumber=10001,
            homeDirectory="/tmp", sn='User',
            mail="t.user1@example.com",
            cn="Test User 1")

        u2 = account.objects.create(
            uid="testuser2", uidNumber=1001, gidNumber=10001,
            homeDirectory="/tmp", sn='User',
            mail="t.user2@example.com",
            cn="Test User 2")

        u3 = account.objects.create(
            uid="testuser3", uidNumber=1002, gidNumber=10001,
            homeDirectory="/tmp", sn='User',
            mail="t.user3@example.com",
            cn="Test User 3")

        g1 = group.objects.create(
            cn="systems", gidNumber=10001,
        )
        g1.secondary_accounts = [u1]

        g2 = group.objects.create(
            cn="empty", gidNumber=10002,
            description="Empty Group",
        )
        g2.secondary_accounts = []

        g3 = group.objects.create(
            cn="full", gidNumber=10003,
        )
        g3.secondary_accounts = [u1, u2, u3]

    def test_get_groups(self):
        self.assertEqual(len(self.group.objects.all()), 3)

    def test_get_group(self):
        g = self.group.objects.get(cn="systems")
        self.assertEqual(g.cn, 'systems')
        g = self.group.objects.get(cn="empty")
        self.assertEqual(g.cn, 'empty')
        g = self.group.objects.get(cn="full")
        self.assertEqual(g.cn, 'full')

    def test_delete_group(self):
        g = self.group.objects.get(cn="full")
        g.delete()
        self.assertEqual(len(self.group.objects.all()), 2)

    def test_update_group(self):
        g = self.group.objects.get(cn="empty")
        self.assertEqual(g.description, 'Empty Group')
        g.description = "No Members"
        g.save()
        g = self.group.objects.get(cn="empty")
        self.assertEqual(g.description, 'No Members')

    def test_update_group_no_modifications(self):
        g = self.group.objects.get(cn="empty")
        self.assertEqual(g.description, 'Empty Group')
        g.description = "Empty Group"
        g.save()
        g = self.group.objects.get(cn="empty")
        self.assertEqual(g.description, 'Empty Group')

    def test_no_group(self):
        self.assertRaises(
            self.group.DoesNotExist, self.group.objects.get, cn='nosuchgroup')

    def test_get_members_empty(self):
        g = self.group.objects.get(cn="empty")
        members = g.secondary_accounts.all()
        self.assertEqual(len(members), 0)
        members = self.account.objects.filter(secondary_groups=g)
        self.assertEqual(len(members), 0)

    def test_get_members_one(self):
        g = self.group.objects.get(cn="systems")
        members = g.secondary_accounts.all()
        self.assertEqual(len(members), 1)
        members = self.account.objects.filter(secondary_groups=g)
        self.assertEqual(len(members), 1)

    def test_get_members_many(self):
        g = self.group.objects.get(cn="full")
        members = g.secondary_accounts.all()
        self.assertEqual(len(members), 3)
        members = self.account.objects.filter(secondary_groups=g)
        self.assertEqual(len(members), 3)

    def test_remove_group_member(self):
        g = self.group.objects.get(cn="full")
        u = g.secondary_accounts.get(uid="testuser2")
        g.secondary_accounts.remove(u)
        members = g.secondary_accounts.all()
        self.assertEqual(len(members), 2)

    def test_remove_group_member_one(self):
        g = self.group.objects.get(cn="systems")
        u = g.secondary_accounts.get(uid="testuser1")
        g.secondary_accounts.remove(u)
        members = g.secondary_accounts.all()
        self.assertEqual(len(members), 0)

    def test_remove_group_member_empty(self):
        g = self.group.objects.get(cn="empty")
        g.secondary_accounts.clear()
        members = g.secondary_accounts.all()
        self.assertEqual(len(members), 0)

    def test_add_member(self):
        g = self.group.objects.get(cn="systems")
        u = self.account.objects.get(uid="testuser2")
        g.secondary_accounts.add(u)
        members = g.secondary_accounts.all()
        self.assertEqual(len(members), 2)

    def test_add_member_empty(self):
        g = self.group.objects.get(cn="empty")
        u = self.account.objects.get(uid="testuser2")
        g.secondary_accounts.add(u)
        members = g.secondary_accounts.all()
        self.assertEqual(len(members), 1)

    def test_add_member_exists(self):
        g = self.group.objects.get(cn="full")
        u = self.account.objects.get(uid="testuser2")
        g.secondary_accounts.add(u)
        members = g.secondary_accounts.all()
        self.assertEqual(len(members), 3)

    def test_add_group(self):
        self.group.objects.create(cn='Admin')
        self.assertEqual(len(self.group.objects.all()), 4)
        g = self.group.objects.get(cn="Admin")
        self.assertEqual(g.gidNumber, 10004)

    def test_add_group_required_attributes(self):
        self.assertRaises(
            tldap.exceptions.ValidationError,
            self.group.objects.create, description='Admin Group')

    def test_add_group_override_generated(self):
        self.group.objects.create(cn='Admin', gidNumber=10008)
        self.assertEqual(len(self.group.objects.all()), 4)
        g = self.group.objects.get(cn="Admin")
        self.assertEqual(g.gidNumber, 10008)

    def test_add_group_optional(self):
        self.group.objects.create(cn='Admin', description='Admin Group')
        self.assertEqual(len(self.group.objects.all()), 4)
        g = self.group.objects.get(cn="Admin")
        self.assertEqual(g.description, 'Admin Group')
