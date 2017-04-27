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
