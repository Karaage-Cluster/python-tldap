#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Copyright 2012 VPAC
#
# This file is part of django-tldap.
#
# django-tldap is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# django-tldap is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with django-tldap  If not, see <http://www.gnu.org/licenses/>.

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import unittest

import tldap
import tldap.schemas.rfc
import tldap.transaction
import tldap.exceptions
import tldap.modlist

import tldap.test.data
import tldap.test.slapd
import schemas as test_schemas

import ldap

server = None


class BackendTest(unittest.TestCase):
    def setUp(self):
        server = tldap.test.slapd.Slapd()
        server.set_port(38911)
        server.start()

        self.server = server
        tldap.connection.reset()

    def tearDown(self):
        self.server.stop()
        tldap.connection.reset()

    def get(self, c, base):
        """
        returns ldap object for search_string
        raises MultipleResultsException if more than one
        entry exists for given search string
        """
        result_data = list(c.search(base, ldap.SCOPE_BASE))
        no_results = len(result_data)
        if no_results < 1:
            raise ldap.NO_SUCH_OBJECT()
        self.assertEqual(no_results, 1)
        return result_data[0][1]

    def test_transactions(self):
        c = tldap.connection

        modlist = tldap.modlist.addModlist({
            'givenName': "Tux",
            'sn': "Torvalds",
            'cn': "Tux Torvalds",
            'telephoneNumber': "000",
            'mail': "tuz@example.org",
            'o': "Linux Rules",
            'userPassword': "silly",
            'objectClass': [
                'top', 'person', 'organizationalPerson', 'inetOrgPerson'],
        })

        c.add("ou=People, dc=python-ldap,dc=org", modlist)

        # test explicit roll back
        with tldap.transaction.commit_on_success():
            c.add("uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [(
                ldap.MOD_REPLACE, "sn", "Gates")])
            c.rollback()
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c,
                          "uid=tux, ou=People, dc=python-ldap,dc=org")

        # test roll back on exception
        try:
            with tldap.transaction.commit_on_success():
                c.add("uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
                c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [(
                    ldap.MOD_REPLACE, "sn", "Gates")])
                raise RuntimeError("testing failure")
        except RuntimeError:
            pass
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c,
                          "uid=tux, ou=People, dc=python-ldap,dc=org")

        # test success commits
        with tldap.transaction.commit_on_success():
            c.add("uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [(
                ldap.MOD_REPLACE, "sn", "Gates")])
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], ["Gates"])
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'],
            ["000"])

        # test deleting attribute *of new object* with rollback
        try:
            with tldap.transaction.commit_on_success():
                c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [
                         (ldap.MOD_DELETE, "telephoneNumber", None)])
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
            ["000"])

        # test deleting attribute *of new object* with success
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [(
                ldap.MOD_DELETE, "telephoneNumber", None)])
            self.assertRaises(KeyError, lambda: self.get(
                c, "uid=tux, ou=People, dc=python-ldap,dc=org")[
                    'telephoneNumber'])
        self.assertRaises(KeyError, lambda: self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'])

        # test adding attribute with rollback
        try:
            with tldap.transaction.commit_on_success():
                c.modify("uid=tux, ou=People, dc=python-ldap,dc=org",
                         [(ldap.MOD_ADD, "telephoneNumber", "111")])
                self.assertEqual(self.get(
                    c, "uid=tux, ou=People, dc=python-ldap,dc=org")[
                        'telephoneNumber'],
                    ["111"])
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
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [(
                ldap.MOD_ADD, "telephoneNumber", "111")])
            self.assertRaises(
                ldap.TYPE_OR_VALUE_EXISTS, c.modify,
                "uid=tux, ou=People, dc=python-ldap,dc=org", [
                (ldap.MOD_ADD, "telephoneNumber", "111")])
            self.assertEqual(self.get(
                c, "uid=tux, ou=People, dc=python-ldap,dc=org")[
                    'telephoneNumber'], ["111"])
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'],
            ["111"])

        # test search scopes
        c.add("ou=Groups, dc=python-ldap,dc=org", [("objectClass",
              ["top", "organizationalunit"])])
        r = c.search("uid=tux, ou=People, dc=python-ldap,dc=org",
                     ldap.SCOPE_BASE, "uid=tux")
        self.assertEqual(len(list(r)), 1)
        r = c.search(
            "ou=People, dc=python-ldap,dc=org", ldap.SCOPE_BASE, "uid=tux")
        self.assertEqual(len(list(r)), 0)
        r = c.search("dc=python-ldap,dc=org", ldap.SCOPE_BASE, "uid=tux")
        self.assertEqual(len(list(r)), 0)
        r = c.search(
            "ou=Groups, dc=python-ldap,dc=org", ldap.SCOPE_BASE, "uid=tux")
        self.assertEqual(len(list(r)), 0)
        r = c.search("dc=python,dc=org", ldap.SCOPE_BASE, "uid=tux")
        self.assertRaises(ldap.NO_SUCH_OBJECT, list, r)

        r = c.search("uid=tux, ou=People, dc=python-ldap,dc=org",
                     ldap.SCOPE_ONELEVEL, "uid=tux")
        self.assertEqual(len(list(r)), 0)
        r = c.search("ou=People, dc=python-ldap,dc=org",
                     ldap.SCOPE_ONELEVEL, "uid=tux")
        self.assertEqual(len(list(r)), 1)
        r = c.search("dc=python-ldap,dc=org", ldap.SCOPE_ONELEVEL, "uid=tux")
        self.assertEqual(len(list(r)), 0)
        r = c.search("ou=Groups, dc=python-ldap,dc=org",
                     ldap.SCOPE_ONELEVEL, "uid=tux")
        self.assertEqual(len(list(r)), 0)
        r = c.search("dc=python,dc=org", ldap.SCOPE_BASE, "uid=tux")
        self.assertRaises(ldap.NO_SUCH_OBJECT, list, r)

        r = c.search("uid=tux, ou=People, dc=python-ldap,dc=org",
                     ldap.SCOPE_SUBTREE, "uid=tux")
        self.assertEqual(len(list(r)), 1)
        r = c.search(
            "ou=People, dc=python-ldap,dc=org", ldap.SCOPE_SUBTREE, "uid=tux")
        self.assertEqual(len(list(r)), 1)
        r = c.search("dc=python-ldap,dc=org", ldap.SCOPE_SUBTREE, "uid=tux")
        self.assertEqual(len(list(r)), 1)
        r = c.search(
            "ou=Groups, dc=python-ldap,dc=org", ldap.SCOPE_SUBTREE, "uid=tux")
        self.assertEqual(len(list(r)), 0)
        r = c.search("dc=python,dc=org", ldap.SCOPE_BASE, "uid=tux")
        self.assertRaises(ldap.NO_SUCH_OBJECT, list, r)

        # test replacing attribute with rollback
        try:
            with tldap.transaction.commit_on_success():
                c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [(
                    ldap.MOD_REPLACE, "telephoneNumber", "222")])
                self.assertEqual(self.get(
                    c, "uid=tux, ou=People, dc=python-ldap,dc=org")[
                        'telephoneNumber'],
                    ["222"])
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()
        except tldap.exceptions.TestFailure:
            pass
        else:
            self.fail("Exception not generated")
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'],
            ["111"])

        # test replacing attribute with success
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [(
                ldap.MOD_REPLACE, "telephoneNumber", "222")])
            self.assertEqual(self.get(
                c, "uid=tux, ou=People, dc=python-ldap,dc=org")[
                    'telephoneNumber'],
                ["222"])
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'],
            ["222"])

        # test deleting attribute value with rollback
        try:
            with tldap.transaction.commit_on_success():
                c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [
                         (ldap.MOD_DELETE, "telephoneNumber", "222")])
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
            ["222"])

        # test deleting attribute value with success
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [(
                ldap.MOD_DELETE, "telephoneNumber", "222")])
            self.assertRaises(
                ldap.NO_SUCH_ATTRIBUTE, c.modify,
                "uid=tux, ou=People, dc=python-ldap,dc=org", [(
                ldap.MOD_DELETE, "telephoneNumber", "222")])
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
                c.modify("uid=tux, ou=People, dc=python-ldap,dc=org",
                         [(ldap.MOD_REPLACE, "sn", "Milkshakes")])
                self.assertEqual(self.get(
                    c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'],
                    ["Milkshakes"])
                c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [(
                    ldap.MOD_REPLACE, "sn", "Bannas")])
                self.assertEqual(self.get(
                    c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'],
                    ["Bannas"])
                self.assertRaises(
                    ldap.ALREADY_EXISTS, c.add,
                    "uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()
        except tldap.exceptions.TestFailure:
            pass
        else:
            self.fail("Exception not generated")
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], ["Gates"])

        # test rename with rollback
        try:
            with tldap.transaction.commit_on_success():
                c.rename(
                    "uid=tux, ou=People, dc=python-ldap,dc=org", 'uid=tuz')
                c.modify("uid=tuz, ou=People, dc=python-ldap,dc=org", [(
                    ldap.MOD_REPLACE, "sn", "Tuz")])
                self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c,
                                  "uid=tux, ou=People, dc=python-ldap,dc=org")
                self.assertEqual(self.get(
                    c, "uid=tuz, ou=People, dc=python-ldap,dc=org")['sn'],
                    ["Tuz"])
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()
        except tldap.exceptions.TestFailure:
            pass
        else:
            self.fail("Exception not generated")
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], ["Gates"])
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c,
                          "uid=tuz, ou=People, dc=python-ldap,dc=org")

        # test rename with success
        with tldap.transaction.commit_on_success():
            c.rename("uid=tux, ou=People, dc=python-ldap,dc=org", 'uid=tuz')
            c.modify("uid=tuz, ou=People, dc=python-ldap,dc=org", [(
                ldap.MOD_REPLACE, "sn", "Tuz")])
            self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c,
                              "uid=tux, ou=People, dc=python-ldap,dc=org")
            self.assertEqual(self.get(
                c, "uid=tuz, ou=People, dc=python-ldap,dc=org")['sn'], ["Tuz"])
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c,
                          "uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(self.get(
            c, "uid=tuz, ou=People, dc=python-ldap,dc=org")['sn'], ["Tuz"])

        # test rename back with success
        with tldap.transaction.commit_on_success():
            c.modify("uid=tuz, ou=People, dc=python-ldap,dc=org", [(
                ldap.MOD_REPLACE, "sn", "Gates")])
            c.rename("uid=tuz, ou=People, dc=python-ldap,dc=org", 'uid=tux')
            self.assertEqual(self.get(
                c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'],
                ["Gates"])
            self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c,
                              "uid=tuz, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], ["Gates"])
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c,
                          "uid=tuz, ou=People, dc=python-ldap,dc=org")

        # test rename with success
        with tldap.transaction.commit_on_success():
            c.rename("uid=tux, ou=People, dc=python-ldap,dc=org", 'cn=tux')
            c.modify("cn=tux, ou=People, dc=python-ldap,dc=org", [(
                ldap.MOD_REPLACE, "sn", "Tuz")])
            self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c,
                              "uid=tux, ou=People, dc=python-ldap,dc=org")
            self.assertEqual(self.get(
                c, "cn=tux, ou=People, dc=python-ldap,dc=org")['sn'], ["Tuz"])
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c,
                          "uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(self.get(
            c, "cn=tux, ou=People, dc=python-ldap,dc=org")['sn'], ["Tuz"])

        # test rename back with success
        with tldap.transaction.commit_on_success():
            c.modify("cn=tux, ou=People, dc=python-ldap,dc=org", [(
                ldap.MOD_REPLACE, "sn", "Gates")])
            c.rename("cn=tux, ou=People, dc=python-ldap,dc=org", 'uid=tux')
            self.assertEqual(self.get(
                c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'],
                ["Gates"])
            self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c,
                              "cn=tux, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], ["Gates"])
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c,
                          "cn=tux, ou=People, dc=python-ldap,dc=org")

        # test rename with success
        with tldap.transaction.commit_on_success():
            c.rename("uid=tux, ou=People, dc=python-ldap,dc=org",
                     'cn=Tux Torvalds')
            c.modify("cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org",
                     [(ldap.MOD_REPLACE, "sn", "Tuz")])
            self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c,
                              "uid=tux, ou=People, dc=python-ldap,dc=org")
            self.assertEqual(self.get(
                c, "cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org")['sn'],
                ["Tuz"])
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c,
                          "uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(self.get(
            c, "cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org")['sn'],
            ["Tuz"])

        # test rename back with success
        with tldap.transaction.commit_on_success():
            c.modify("cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org",
                     [(ldap.MOD_REPLACE, "sn", "Gates")])
            c.modify("cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org", [(
                ldap.MOD_ADD, "cn", ["meow"])])
            c.rename(
                "cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org", 'uid=tux')
            c.modify("uid=Tux, ou=People, dc=python-ldap,dc=org", [(
                ldap.MOD_REPLACE, "cn", "Tux Torvalds")])
            self.assertEqual(self.get(
                c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'],
                ["Gates"])
            self.assertEqual(self.get(
                c, "uid=tux, ou=People, dc=python-ldap,dc=org")['cn'],
                ["Tux Torvalds"])
            self.assertRaises(
                ldap.NO_SUCH_OBJECT, self.get, c,
                "cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], ["Gates"])
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['cn'],
            ["Tux Torvalds"])
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c,
                          "cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org")

        # test roll back on error of delete and add of same user
        try:
            with tldap.transaction.commit_on_success():
                c.delete("uid=tux, ou=People, dc=python-ldap,dc=org")
                self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c,
                                  "uid=tux, ou=People, dc=python-ldap,dc=org")
                c.add("uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
                self.assertRaises(ldap.ALREADY_EXISTS, c.add,
                                  "uid=tux, ou=People, dc=python-ldap,dc=org",
                                  modlist)
                c.fail()  # raises TestFailure during commit causing rollback
                c.commit()
        except tldap.exceptions.TestFailure:
            pass
        else:
            self.fail("Exception not generated")
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], ["Gates"])

        # test delate and add same user
        with tldap.transaction.commit_on_success():
            c.delete("uid=tux, ou=People, dc=python-ldap,dc=org")
            self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c,
                              "uid=tux, ou=People, dc=python-ldap,dc=org")
            c.add("uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
        self.assertEqual(self.get(
            c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'],
            ["Torvalds"])

        # test delate
        with tldap.transaction.commit_on_success():
            c.delete("uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c,
                          "uid=tux, ou=People, dc=python-ldap,dc=org")


class ModelTest(unittest.TestCase):
    def setUp(self):
        server = tldap.test.slapd.Slapd()
        server.set_port(38911)
        server.start()

        self.server = server
        tldap.connection.reset()

    def tearDown(self):
        self.server.stop()
        tldap.connection.reset()

    def test_transactions(self):
        organizationalUnit = tldap.schemas.rfc.organizationalUnit
        organizationalUnit.objects.create(
            dn="ou=People, dc=python-ldap,dc=org")

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
        return

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
            'o': "Linux Rules £",
            'userPassword': "silly",
        }
        p1 = person.objects.create(uid="tux", **kwargs)
        p2 = person.objects.create(uid="tuz", **kwargs)
        g1 = group.objects.create(cn="group1", gidNumber=10, memberUid=["tux"])
        g2 = group.objects.create(
            cn="group2", gidNumber=11, memberUid=["tux", "tuz"])

        self.assertEqual(
            person.objects.all()._get_filter(tldap.Q(uid='t\ux')),
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
            )._get_filter(tldap.Q(uid='tux') & tldap.Q(uid='tuz')),
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


class UserAPITest(unittest.TestCase):
    def setUp(self):
        server = tldap.test.slapd.Slapd()
        server.set_port(38911)
        server.start()

        server.ldapadd("\n".join(tldap.test.data.test_ldif) + "\n")

        self.server = server
        tldap.connection.reset()

        self.group = test_schemas.group
        self.account = test_schemas.account

    def tearDown(self):
        self.server.stop()
        tldap.connection.reset()

    def test_get_users(self):
        self.failUnlessEqual(len(self.account.objects.all()), 3)

    def test_get_user(self):
        u = self.account.objects.get(uid='testuser3')
        self.failUnlessEqual(u.mail, 't.user3@example.com')

    def test_delete_user(self):
        self.failUnlessEqual(len(self.account.objects.all()), 3)
        u = self.account.objects.get(uid='testuser2')
        u.delete()
        self.failUnlessEqual(len(self.account.objects.all()), 2)

    def test_in_ldap(self):
        self.account.objects.get(uid='testuser1')
        self.failUnlessRaises(self.account.DoesNotExist,
                              self.account.objects.get, cn='testuser4')

    def test_update_user(self):
        u = self.account.objects.get(uid='testuser1')
        self.failUnlessEqual(u.sn, 'User')
        u.sn = "Bloggs"
        u.save()
        u = self.account.objects.get(uid='testuser1')
        self.failUnlessEqual(u.sn, 'Bloggs')

    def test_update_user_no_modifications(self):
        u = self.account.objects.get(uid='testuser1')
        self.failUnlessEqual(u.sn, 'User')
        u.sn = "User"
        u.save()
        u = self.account.objects.get(uid='testuser1')
        self.failUnlessEqual(u.sn, 'User')

#    def test_lock_unlock(self):
#        u = self.account.objects.get(uid='testuser1')
#        u.unlock()
#        u.save()
#
#        u = self.account.objects.get(uid='testuser1')
#        self.failUnlessEqual(u.is_locked(), False)
#        u.lock()
#        u.save()
#
#        u = self.account.objects.get(uid='testuser1')
#        self.failUnlessEqual(u.is_locked(), True)
#
#        u.unlock()
#        u.save()
#        self.failUnlessEqual(u.is_locked(), False)

    def test_user_slice(self):
        self.account.objects.get(uid='testuser1').save()
        users = self.account.objects.filter(
            tldap.Q(cn__contains='nothing') | tldap.Q(cn__contains="user"))
        self.failUnlessEqual(users[0].uid, "testuser1")
        self.failUnlessEqual(users[1].uid, "testuser2")
        self.failUnlessEqual(users[2].uid, "testuser3")
        self.failUnlessRaises(IndexError, users.__getitem__, 3)
        a = iter(users[1:4])
        self.failUnlessEqual(a.next().uid, "testuser2")
        self.failUnlessEqual(a.next().uid, "testuser3")
        self.failUnlessRaises(StopIteration, a.next)

    def test_user_search(self):
        self.account.objects.get(uid='testuser1').save()
        users = self.account.objects.filter(cn__contains='User')
        self.failUnlessEqual(len(users), 3)

    def test_user_search_one(self):
        self.account.objects.get(uid='testuser1').save()
        users = self.account.objects.filter(uid__contains='testuser1')
        self.failUnlessEqual(len(users), 1)

    def test_user_search_empty(self):
        self.account.objects.get(uid='testuser1').save()
        users = self.account.objects.filter(cn__contains='nothing')
        self.failUnlessEqual(len(users), 0)

    def test_user_search_multi(self):
        self.account.objects.get(uid='testuser1').save()
        users = self.account.objects.filter(
            tldap.Q(cn__contains='nothing') | tldap.Q(cn__contains="user"))
        self.failUnlessEqual(len(users), 3)

    def test_get_groups_empty(self):
        u = self.account.objects.get(uid="testuser2")
        u.secondary_groups.clear()
        groups = u.secondary_groups.all()
        self.failUnlessEqual(len(groups), 0)
        groups = self.group.objects.filter(secondary_accounts=u)
        self.failUnlessEqual(len(groups), 0)

    def test_get_groups_one(self):
        u = self.account.objects.get(uid="testuser2")
        groups = u.secondary_groups.all()
        self.failUnlessEqual(len(groups), 1)
        groups = self.group.objects.filter(secondary_accounts=u)
        self.failUnlessEqual(len(groups), 1)

    def test_get_groups_many(self):
        u = self.account.objects.get(uid="testuser1")
        groups = u.secondary_groups.all()
        self.failUnlessEqual(len(groups), 2)
        groups = self.group.objects.filter(secondary_accounts=u)
        self.failUnlessEqual(len(groups), 2)


class GroupAPITest(unittest.TestCase):
    def setUp(self):
        server = tldap.test.slapd.Slapd()
        server.set_port(38911)
        server.start()

        server.ldapadd("\n".join(tldap.test.data.test_ldif) + "\n")

        self.server = server
        tldap.connection.reset()

        self.group = test_schemas.group
        self.account = test_schemas.account

    def tearDown(self):
        self.server.stop()
        tldap.connection.reset()

    def test_get_groups(self):
        self.failUnlessEqual(len(self.group.objects.all()), 3)

    def test_get_group(self):
        g = self.group.objects.get(cn="systems")
        self.failUnlessEqual(g.cn, 'systems')
        g = self.group.objects.get(cn="empty")
        self.failUnlessEqual(g.cn, 'empty')
        g = self.group.objects.get(cn="full")
        self.failUnlessEqual(g.cn, 'full')

    def test_delete_group(self):
        g = self.group.objects.get(cn="full")
        g.delete()
        self.failUnlessEqual(len(self.group.objects.all()), 2)

    def test_update_group(self):
        g = self.group.objects.get(cn="empty")
        self.failUnlessEqual(g.description, 'Empty Group')
        g.description = "No Members"
        g.save()
        g = self.group.objects.get(cn="empty")
        self.failUnlessEqual(g.description, 'No Members')

    def test_update_group_no_modifications(self):
        g = self.group.objects.get(cn="empty")
        self.failUnlessEqual(g.description, 'Empty Group')
        g.description = "Empty Group"
        g.save()
        g = self.group.objects.get(cn="empty")
        self.failUnlessEqual(g.description, 'Empty Group')

    def test_no_group(self):
        self.failUnlessRaises(
            self.group.DoesNotExist, self.group.objects.get, cn='nosuchgroup')

    def test_get_members_empty(self):
        g = self.group.objects.get(cn="empty")
        members = g.secondary_accounts.all()
        self.failUnlessEqual(len(members), 0)
        members = self.account.objects.filter(secondary_groups=g)
        self.failUnlessEqual(len(members), 0)

    def test_get_members_one(self):
        g = self.group.objects.get(cn="systems")
        members = g.secondary_accounts.all()
        self.failUnlessEqual(len(members), 1)
        members = self.account.objects.filter(secondary_groups=g)
        self.failUnlessEqual(len(members), 1)

    def test_get_members_many(self):
        g = self.group.objects.get(cn="full")
        members = g.secondary_accounts.all()
        self.failUnlessEqual(len(members), 3)
        members = self.account.objects.filter(secondary_groups=g)
        self.failUnlessEqual(len(members), 3)

    def test_remove_group_member(self):
        g = self.group.objects.get(cn="full")
        u = g.secondary_accounts.get(uid="testuser2")
        g.secondary_accounts.remove(u)
        members = g.secondary_accounts.all()
        self.failUnlessEqual(len(members), 2)

    def test_remove_group_member_one(self):
        g = self.group.objects.get(cn="systems")
        u = g.secondary_accounts.get(uid="testuser1")
        g.secondary_accounts.remove(u)
        members = g.secondary_accounts.all()
        self.failUnlessEqual(len(members), 0)

    def test_remove_group_member_empty(self):
        g = self.group.objects.get(cn="empty")
        g.secondary_accounts.clear()
        members = g.secondary_accounts.all()
        self.failUnlessEqual(len(members), 0)

    def test_add_member(self):
        g = self.group.objects.get(cn="systems")
        u = self.account.objects.get(uid="testuser2")
        g.secondary_accounts.add(u)
        members = g.secondary_accounts.all()
        self.failUnlessEqual(len(members), 2)

    def test_add_member_empty(self):
        g = self.group.objects.get(cn="empty")
        u = self.account.objects.get(uid="testuser2")
        g.secondary_accounts.add(u)
        members = g.secondary_accounts.all()
        self.failUnlessEqual(len(members), 1)

    def test_add_member_exists(self):
        g = self.group.objects.get(cn="full")
        u = self.account.objects.get(uid="testuser2")
        g.secondary_accounts.add(u)
        members = g.secondary_accounts.all()
        self.failUnlessEqual(len(members), 3)

    def test_add_group(self):
        self.group.objects.create(cn='Admin')
        self.failUnlessEqual(len(self.group.objects.all()), 4)
        g = self.group.objects.get(cn="Admin")
        self.failUnlessEqual(g.gidNumber, 10004)

    def test_add_group_required_attributes(self):
        self.failUnlessRaises(
            tldap.exceptions.ValidationError,
            self.group.objects.create, description='Admin Group')

    def test_add_group_override_generated(self):
        self.group.objects.create(cn='Admin', gidNumber=10008)
        self.failUnlessEqual(len(self.group.objects.all()), 4)
        g = self.group.objects.get(cn="Admin")
        self.failUnlessEqual(g.gidNumber, 10008)

    def test_add_group_optional(self):
        self.group.objects.create(cn='Admin', description='Admin Group')
        self.failUnlessEqual(len(self.group.objects.all()), 4)
        g = self.group.objects.get(cn="Admin")
        self.failUnlessEqual(g.description, 'Admin Group')

if __name__ == '__main__':
    unittest.main()
