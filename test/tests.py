#!/usr/bin/python

# Copyright 2012 VPAC
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


import django.core.management
import test.settings
django.core.management.setup_environ(test.settings)

import unittest

import tldap
import tldap.test.slapd
import tldap.transaction
import tldap.exceptions

import ldap.modlist

def assert_cache_dn(ut, dn, c):
        dn = c._cache_normalize_dn(dn)

        try:
            result_data = c._obj.search_s(dn, ldap.SCOPE_BASE)
        except ldap.NO_SUCH_OBJECT:
            result_data = []

        if dn not in c._cache:
            return

        if c._cache[dn] is None:
            ut.assertEqual(len(result_data), 0)
            return

        ut.assertEqual(len(result_data), 1)
        ut.assertEqual(result_data[0][0].lower(), dn)
        ut.assertEqual(result_data[0][1], c._cache[dn])

def raise_testfailure(place):
    raise TestFailure("fail %s called"%place)

server = None

class BackendTest(unittest.TestCase):
    def setUp(self):
        global server
        server = tldap.test.slapd.Slapd()
        server.set_port(38911)
        server.start()
        base = server.get_dn_suffix()

        self.server = server
        tldap.connection.reset(forceflushcache=True)

    def tearDown(self):
        self.server.stop()
        tldap.connection.reset(forceflushcache=True)


    def get(self, c, base):
        """
        returns ldap object for search_string
        raises MultipleResultsException if more than one 
        entry exists for given search string
        """
        result_data = c.search(base, ldap.SCOPE_BASE)
        no_results = len(result_data)
        if no_results < 1:
            raise ldap.NO_SUCH_OBJECT()
        self.assertEqual(no_results, 1)
        return result_data[0][1]

    def test_transactions(self):
        c = tldap.connection
        c.autoflushcache = False

        modlist = ldap.modlist.addModlist({
            'givenName': "Tux",
            'sn': "Torvalds",
            'cn': "Tux Torvalds",
            'telephoneNumber': "000",
            'mail': "tuz@example.org",
            'o': "Linux Rules",
            'userPassword': "silly",
            'objectClass': ['top', 'person', 'organizationalPerson', 'inetOrgPerson' ],
        })

        c.add("ou=People, dc=python-ldap,dc=org", modlist)

        # test explicit roll back
        with tldap.transaction.commit_on_success():
            c.add("uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "sn", "Gates") ])
            c.rollback()
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tux, ou=People, dc=python-ldap,dc=org")
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test roll back on exception
        try:
            with tldap.transaction.commit_on_success():
                c.add("uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
                c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "sn", "Gates") ])
                raise RuntimeError("testing failure")
        except RuntimeError:
            pass
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tux, ou=People, dc=python-ldap,dc=org")
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test success commits
        with tldap.transaction.commit_on_success():
            c.add("uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "sn", "Gates") ])
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [ "Gates" ])
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "000" ])
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test deleting attribute *of new object* with rollback
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_DELETE, "telephoneNumber", None) ])
            self.assertRaises(KeyError, lambda: self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'])
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "000" ])
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test deleting attribute *of new object* with success
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_DELETE, "telephoneNumber", None) ])
            self.assertRaises(KeyError, lambda: self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'])
        self.assertRaises(KeyError, lambda: self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'])
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test adding attribute with rollback
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_ADD, "telephoneNumber", "111") ])
            self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "111" ])
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertRaises(KeyError, lambda: self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'])
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test adding attribute with success
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_ADD, "telephoneNumber", "111") ])
            self.assertRaises(ldap.TYPE_OR_VALUE_EXISTS, c.modify, "uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_ADD, "telephoneNumber", "111") ])
            self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "111" ])
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "111" ])
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test search scopes
        c.add("ou=Groups, dc=python-ldap,dc=org", [ ("objectClass", ["top","organizationalunit"]) ])
        r = c.search("uid=tux, ou=People, dc=python-ldap,dc=org", ldap.SCOPE_BASE, "uid=tux")
        self.assertEqual(len(r), 1)
        r = c.search("ou=People, dc=python-ldap,dc=org", ldap.SCOPE_BASE, "uid=tux")
        self.assertEqual(len(r), 0)
        r = c.search("dc=python-ldap,dc=org", ldap.SCOPE_BASE, "uid=tux")
        self.assertEqual(len(r), 0)
        r = c.search("ou=Groups, dc=python-ldap,dc=org", ldap.SCOPE_BASE, "uid=tux")
        self.assertEqual(len(r), 0)
        self.assertRaises(ldap.NO_SUCH_OBJECT, c.search, "dc=python,dc=org", ldap.SCOPE_BASE, "uid=tux")
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        r = c.search("uid=tux, ou=People, dc=python-ldap,dc=org", ldap.SCOPE_ONELEVEL, "uid=tux")
        self.assertEqual(len(r), 1)
        r = c.search("ou=People, dc=python-ldap,dc=org", ldap.SCOPE_ONELEVEL, "uid=tux")
        self.assertEqual(len(r), 1)
        r = c.search("dc=python-ldap,dc=org", ldap.SCOPE_ONELEVEL, "uid=tux")
        self.assertEqual(len(r), 0)
        r = c.search("ou=Groups, dc=python-ldap,dc=org", ldap.SCOPE_ONELEVEL, "uid=tux")
        self.assertEqual(len(r), 0)
        self.assertRaises(ldap.NO_SUCH_OBJECT, c.search, "dc=python,dc=org", ldap.SCOPE_BASE, "uid=tux")
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        r = c.search("uid=tux, ou=People, dc=python-ldap,dc=org", ldap.SCOPE_SUBTREE, "uid=tux")
        self.assertEqual(len(r), 1)
        r = c.search("ou=People, dc=python-ldap,dc=org", ldap.SCOPE_SUBTREE, "uid=tux")
        self.assertEqual(len(r), 1)
        r = c.search("dc=python-ldap,dc=org", ldap.SCOPE_SUBTREE, "uid=tux")
        self.assertEqual(len(r), 1)
        r = c.search("ou=Groups, dc=python-ldap,dc=org", ldap.SCOPE_SUBTREE, "uid=tux")
        self.assertEqual(len(r), 0)
        self.assertRaises(ldap.NO_SUCH_OBJECT, c.search, "dc=python,dc=org", ldap.SCOPE_BASE, "uid=tux")
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test replacing attribute with rollback
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "telephoneNumber", "222") ])
            self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "222" ])
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "111" ])
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test replacing attribute with success
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "telephoneNumber", "222") ])
            self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "222" ])
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "222" ])
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test deleting attribute value with rollback
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_DELETE, "telephoneNumber", "222") ])
            self.assertRaises(KeyError, lambda: self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'])
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "222" ])
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test deleting attribute value with success
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_DELETE, "telephoneNumber", "222") ])
            self.assertRaises(ldap.NO_SUCH_ATTRIBUTE, c.modify, "uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_DELETE, "telephoneNumber", "222") ])
            self.assertRaises(KeyError, lambda: self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'])
        self.assertRaises(KeyError, lambda: self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'])
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test success when 3rd statement fails; need to roll back 2nd and 1st statements
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "sn", "Milkshakes") ])
            self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [ "Milkshakes" ])
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "sn", "Bannas") ])
            self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [ "Bannas" ])
            self.assertRaises(ldap.ALREADY_EXISTS, c.add, "uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [ "Gates" ])
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test rename with rollback
        with tldap.transaction.commit_on_success():
            c.rename("uid=tux, ou=People, dc=python-ldap,dc=org", 'uid=tuz')
            c.modify("uid=tuz, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "sn", "Tuz") ])
            self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tux, ou=People, dc=python-ldap,dc=org")
            self.assertEqual(self.get(c, "uid=tuz, ou=People, dc=python-ldap,dc=org")['sn'], [ "Tuz" ])
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [ "Gates" ])
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tuz, ou=People, dc=python-ldap,dc=org")
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)
        assert_cache_dn(self, "uid=tuz, ou=People, dc=python-ldap,dc=org", c)

        # test rename with success
        with tldap.transaction.commit_on_success():
            c.rename("uid=tux, ou=People, dc=python-ldap,dc=org", 'uid=tuz')
            c.modify("uid=tuz, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "sn", "Tuz") ])
            self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tux, ou=People, dc=python-ldap,dc=org")
            self.assertEqual(self.get(c, "uid=tuz, ou=People, dc=python-ldap,dc=org")['sn'], [ "Tuz" ])
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(self.get(c, "uid=tuz, ou=People, dc=python-ldap,dc=org")['sn'], [ "Tuz" ])
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)
        assert_cache_dn(self, "uid=tuz, ou=People, dc=python-ldap,dc=org", c)

        # test rename back with success
        with tldap.transaction.commit_on_success():
            c.modify("uid=tuz, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "sn", "Gates") ])
            c.rename("uid=tuz, ou=People, dc=python-ldap,dc=org", 'uid=tux')
            self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [ "Gates" ])
            self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tuz, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [ "Gates" ])
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tuz, ou=People, dc=python-ldap,dc=org")
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)
        assert_cache_dn(self, "uid=tuz, ou=People, dc=python-ldap,dc=org", c)

        # test rename with success
        with tldap.transaction.commit_on_success():
            c.rename("uid=tux, ou=People, dc=python-ldap,dc=org", 'cn=tux')
            c.modify("cn=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "sn", "Tuz") ])
            self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tux, ou=People, dc=python-ldap,dc=org")
            self.assertEqual(self.get(c, "cn=tux, ou=People, dc=python-ldap,dc=org")['sn'], [ "Tuz" ])
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(self.get(c, "cn=tux, ou=People, dc=python-ldap,dc=org")['sn'], [ "Tuz" ])
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)
        assert_cache_dn(self, "cn=tux, ou=People, dc=python-ldap,dc=org", c)

        # test rename back with success
        with tldap.transaction.commit_on_success():
            c.modify("cn=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "sn", "Gates") ])
            c.rename("cn=tux, ou=People, dc=python-ldap,dc=org", 'uid=tux')
            self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [ "Gates" ])
            self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "cn=tux, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [ "Gates" ])
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "cn=tux, ou=People, dc=python-ldap,dc=org")
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)
        assert_cache_dn(self, "cn=tux, ou=People, dc=python-ldap,dc=org", c)

        # test rename with success
        with tldap.transaction.commit_on_success():
            c.rename("uid=tux, ou=People, dc=python-ldap,dc=org", 'cn=Tux Torvalds')
            c.modify("cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "sn", "Tuz") ])
            self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tux, ou=People, dc=python-ldap,dc=org")
            self.assertEqual(self.get(c, "cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org")['sn'], [ "Tuz" ])
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(self.get(c, "cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org")['sn'], [ "Tuz" ])
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)
        assert_cache_dn(self, "cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org", c)

        # test rename back with success
        with tldap.transaction.commit_on_success():
            c.modify("cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "sn", "Gates") ])
            c.modify("cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_ADD, "cn", [ "meow" ] ) ])
            c.rename("cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org", 'uid=tux')
            c.modify("uid=Tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "cn", "Tux Torvalds" ) ])
            self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [ "Gates" ])
            self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['cn'], [ "Tux Torvalds" ])
            self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [ "Gates" ])
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['cn'], [ "Tux Torvalds" ])
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org")
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)
        assert_cache_dn(self, "cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org", c)

        # test roll back on error of delete and add of same user
        with tldap.transaction.commit_on_success():
            c.delete("uid=tux, ou=People, dc=python-ldap,dc=org")
            self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tux, ou=People, dc=python-ldap,dc=org")
            c.add("uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
            self.assertRaises(ldap.ALREADY_EXISTS, c.add, "uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [ "Gates" ])
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)
        assert_cache_dn(self, "uid=tuz, ou=People, dc=python-ldap,dc=org", c)

        # test delate and add same user
        with tldap.transaction.commit_on_success():
            c.delete("uid=tux, ou=People, dc=python-ldap,dc=org")
            self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tux, ou=People, dc=python-ldap,dc=org")
            c.add("uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [ "Torvalds" ])
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)
        assert_cache_dn(self, "uid=tuz, ou=People, dc=python-ldap,dc=org", c)

        # test delate
        with tldap.transaction.commit_on_success():
            c.delete("uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tux, ou=People, dc=python-ldap,dc=org")
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)
        assert_cache_dn(self, "uid=tuz, ou=People, dc=python-ldap,dc=org", c)

        c.autoflushcache = True


import tldap.models

class ModelTest(unittest.TestCase):
    def setUp(self):
        global server
        server = tldap.test.slapd.Slapd()
        server.set_port(38911)
        server.start()
        base = server.get_dn_suffix()

        self.server = server
        tldap.connection.reset(forceflushcache=True)

    def tearDown(self):
        self.server.stop()
        tldap.connection.reset(forceflushcache=True)

    def test_transactions(self):
        organizationalUnit = tldap.models.organizationalUnit
        organizationalUnit.objects.create(dn="ou=People, dc=python-ldap,dc=org", ou="People")

        c = tldap.connection
        c.autoflushcache = False

        person = tldap.models.person
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
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

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
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test success commits
        with tldap.transaction.commit_on_success():
            p = create(uid="tux", **kwargs)
            p.sn = "Gates"
            p.save()
        self.assertEqual(get(uid="tux").sn, "Gates")
        self.assertEqual(get(uid="tux").telephoneNumber, "000")
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)


        # test deleting attribute
        p, created = get_or_create(uid="tux")
        self.assertEqual(created, False)
        p.telephoneNumber = None
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test deleting attribute *of new object* with rollback
        with tldap.transaction.commit_on_success():
            p.save()
            self.assertEqual(get(uid="tux").telephoneNumber, None)
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertEqual(get(uid="tux").telephoneNumber, "000")
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test deleting attribute *of new object* with success
        with tldap.transaction.commit_on_success():
            p.save()
            self.assertEqual(get(uid="tux").telephoneNumber, None)
        self.assertEqual(get(uid="tux").telephoneNumber, None)
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test adding attribute
        p, created = get_or_create(uid="tux")
        self.assertEqual(created, False)
        p.telephoneNumber = "111"
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test adding attribute with rollback
        with tldap.transaction.commit_on_success():
            p.save()
            self.assertEqual(get(uid="tux").telephoneNumber, "111")
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertEqual(get(uid="tux").telephoneNumber, None)
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)
        # test adding attribute with success
        with tldap.transaction.commit_on_success():
            p.save()
            self.assertEqual(get(uid="tux").telephoneNumber, "111")
        self.assertEqual(get(uid="tux").telephoneNumber, "111")
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test replacing attribute
        p, created = get_or_create(uid="tux")
        self.assertEqual(created, False)
        p.telephoneNumber = "222"
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test replacing attribute with rollback
        with tldap.transaction.commit_on_success():
            p.save()
            self.assertEqual(get(uid="tux").telephoneNumber, "222")
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertEqual(get(uid="tux").telephoneNumber, "111")

        # test replacing attribute with success
        with tldap.transaction.commit_on_success():
            p.save()
            self.assertEqual(get(uid="tux").telephoneNumber, "222")
        self.assertEqual(get(uid="tux").telephoneNumber, "222")
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test deleting attribute
        p, created = get_or_create(uid="tux")
        self.assertEqual(created, False)
        p.telephoneNumber = None
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test deleting attribute *of new object* with rollback
        with tldap.transaction.commit_on_success():
            p.save()
            self.assertEqual(get(uid="tux").telephoneNumber, None)
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertEqual(get(uid="tux").telephoneNumber, "222")
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test deleting attribute *of new object* with success
        with tldap.transaction.commit_on_success():
            p.save()
            self.assertEqual(get(uid="tux").telephoneNumber, None)
        self.assertEqual(get(uid="tux").telephoneNumber, None)
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test success when 3rd statement fails; need to roll back 2nd and 1st statements
        with tldap.transaction.commit_on_success():
            p = get(uid="tux")
            p.sn = "Milkshakes"
            p.save()
            self.assertEqual(get(uid="tux").sn, "Milkshakes")

            p.sn = "Bannas"
            p.save()
            self.assertEqual(get(uid="tux").sn, "Bannas")

            self.assertRaises(AlreadyExists, lambda: p.save(force_add=True))
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertEqual(get(uid="tux").sn, "Gates")
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test delate and add same user
        with tldap.transaction.commit_on_success():
            p = get(uid="tux")
            p.delete()
            self.assertRaises(DoesNotExist, get, uid="tux")
            p.save()
            self.assertEqual(get(uid="tux").sn, "Gates")
        self.assertEqual(get(uid="tux").sn, "Gates")
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        # test rename with rollback
        with tldap.transaction.commit_on_success():
            p = get(uid="tux")
            p.rename('uid', 'tuz')
            p.sn = "Tuz"
            p.save()
            self.assertRaises(DoesNotExist, get, uid="tux")
            self.assertEqual(get(uid="tuz").sn, "Tuz")
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertEqual(get(uid="tux").sn, "Gates")
        self.assertRaises(DoesNotExist, get, uid="tuz")
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)
        assert_cache_dn(self, "uid=tuz, ou=People, dc=python-ldap,dc=org", c)

        # test rename with success
        with tldap.transaction.commit_on_success():
            p = get(uid="tux")
            p.rename('uid', 'tuz')
            p.sn = "Tuz"
            p.save()
            self.assertRaises(DoesNotExist, get, uid="tux")
            self.assertEqual(get(uid="tuz").sn, "Tuz")
        self.assertRaises(DoesNotExist, get, uid="tux")
        self.assertEqual(get(uid="tuz").sn, "Tuz")
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)
        assert_cache_dn(self, "uid=tuz, ou=People, dc=python-ldap,dc=org", c)

        # test rename back with success
        with tldap.transaction.commit_on_success():
            p = get(uid="tuz")
            p.rename('uid', 'tux')
            p.sn = "Gates"
            p.save()
            self.assertEqual(get(uid="tux").sn, "Gates")
            self.assertRaises(DoesNotExist, get, uid="tuz")
        self.assertEqual(get(uid="tux").sn, "Gates")
        self.assertRaises(DoesNotExist, get, uid="tuz")
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)
        assert_cache_dn(self, "uid=tuz, ou=People, dc=python-ldap,dc=org", c)

        # hack for testing
        for i in p._meta.fields:
            if i.name == "cn":
                i._max_instances = 2

        # test rename with success
        with tldap.transaction.commit_on_success():
            p = get(uid="tux")
            p.rename('cn', 'tux')
            self.assertEqual(p.cn, [ "Tux Torvalds", "tux" ])
            p.sn = "Tuz"
            p.save()
            self.assertRaises(DoesNotExist, get, uid="tux")
            self.assertEqual(get(dn="cn=tux, ou=People, dc=python-ldap,dc=org").sn, "Tuz")
            self.assertEqual(get(dn="cn=tux, ou=People, dc=python-ldap,dc=org").uid, None)
            self.assertEqual(get(dn="cn=tux, ou=People, dc=python-ldap,dc=org").cn, [ "Tux Torvalds", "tux" ])
        self.assertRaises(DoesNotExist, get, uid="tux")
        self.assertEqual(get(dn="cn=tux, ou=People, dc=python-ldap,dc=org").sn, "Tuz")
        self.assertEqual(get(dn="cn=tux, ou=People, dc=python-ldap,dc=org").uid, None)
        self.assertEqual(get(dn="cn=tux, ou=People, dc=python-ldap,dc=org").cn, [ "Tux Torvalds", "tux" ])
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)
        assert_cache_dn(self, "cn=tux, ou=People, dc=python-ldap,dc=org", c)

        # test rename back with success
        with tldap.transaction.commit_on_success():
            p = get(dn="cn=tux, ou=People, dc=python-ldap,dc=org")
            p.rename('uid', 'tux')
            self.assertEqual(p.cn, [ "Tux Torvalds" ])
            p.sn = "Gates"
            p.save()
            self.assertEqual(get(uid="tux").sn, "Gates")
            self.assertRaises(DoesNotExist, get, dn="cn=tux, ou=People, dc=python-ldap,dc=org")
            self.assertEqual(get(uid="tux").uid, "tux")
            self.assertEqual(get(uid="tux").cn, [ "Tux Torvalds" ])
        self.assertEqual(get(uid="tux").sn, "Gates")
        self.assertRaises(DoesNotExist, get, dn="cn=tux, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(get(uid="tux").uid, "tux")
        self.assertEqual(get(uid="tux").cn, [ "Tux Torvalds" ])
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)
        assert_cache_dn(self, "cn=tux, ou=People, dc=python-ldap,dc=org", c)

        # test rename with success
        with tldap.transaction.commit_on_success():
            p = get(uid="tux")
            p.rename('cn', 'Tux Torvalds')
            self.assertEqual(p.cn, [ "Tux Torvalds" ])
            p.sn = "Tuz"
            p.save()
            self.assertRaises(DoesNotExist, get, uid="tux")
            self.assertEqual(get(dn="cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org").sn, "Tuz")
            self.assertEqual(get(dn="cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org").uid, None)
            self.assertEqual(get(dn="cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org").cn, [ "Tux Torvalds" ])
        self.assertRaises(DoesNotExist, get, uid="tux")
        self.assertEqual(get(dn="cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org").sn, "Tuz")
        self.assertEqual(get(dn="cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org").uid, None)
        self.assertEqual(get(dn="cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org").cn, [ "Tux Torvalds" ])
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)
        assert_cache_dn(self, "cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org", c)

        # test rename back with success
        with tldap.transaction.commit_on_success():
            p = get(dn="cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org")
            p.cn = [ 'sss', 'Tux Torvalds' ]
            p.save()
            p.rename('uid', 'tux')
            self.assertEqual(p.cn, [ "sss", "Tux Torvalds" ])
            p.sn = "Gates"
            p.cn = ['Tux Torvalds' ]
            p.save()
            self.assertEqual(get(uid="tux").sn, "Gates")
            self.assertRaises(DoesNotExist, get, dn="cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org")
            self.assertEqual(get(uid="tux").uid, "tux")
            self.assertEqual(get(uid="tux").cn, [ "Tux Torvalds" ])
        self.assertEqual(get(uid="tux").sn, "Gates")
        self.assertRaises(DoesNotExist, get, dn="cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(get(uid="tux").uid, "tux")
        self.assertEqual(get(uid="tux").cn, [ "Tux Torvalds" ])
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)
        assert_cache_dn(self, "cn=Tux Torvalds, ou=People, dc=python-ldap,dc=org", c)

        # unhack for testing
        for i in p._meta.fields:
            if i.name == "cn":
                i._max_instances = 1

        # test roll back on error of delete and add of same user
        old_p = p
        with tldap.transaction.commit_on_success():
            p.delete()
            self.assertRaises(DoesNotExist, get, uid="tux")
            p = create(uid="tux", **kwargs)
            self.assertRaises(AlreadyExists, create, uid="tux", **kwargs)
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertEqual(get(uid="tux").sn, "Gates")
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)
        assert_cache_dn(self, "uid=tuz, ou=People, dc=python-ldap,dc=org", c)

        # test delate
        with tldap.transaction.commit_on_success():
            old_p.delete()
        self.assertRaises(DoesNotExist, get, uid="tux")
        assert_cache_dn(self, "uid=tux, ou=People, dc=python-ldap,dc=org", c)

        c.autoflushcache = True

        return

    def test_query(self):
        organizationalUnit = tldap.models.organizationalUnit
        organizationalUnit.objects.create(dn="ou=People, dc=python-ldap,dc=org", ou="People")

        organizationalUnit = tldap.models.organizationalUnit
        organizationalUnit.objects.create(dn="ou=Group, dc=python-ldap,dc=org", ou="Group")

        person = tldap.models.person
        group = tldap.models.posix_group

        kwargs = {
            'givenName': "Tux",
            'sn': "Torvalds",
            'cn': "Tux Torvalds",
            'telephoneNumber': "000",
            'mail': "tuz@example.org",
            'o': "Linux Rules",
            'userPassword': "silly",
        }
        p1 = person.objects.create(uid="tux", **kwargs)
        p2 = person.objects.create(uid="tuz", **kwargs)
        g1 = group.objects.create(cn="group1", gidNumber=10, memberUid="tux")
        g2 = group.objects.create(cn="group2", gidNumber=11, memberUid=[ "tux", "tuz" ])

        self.assertEqual(
            person.objects.all()._get_filter(tldap.Q(uid='t\ux')),
            "(&(uid=t\\5cux))")
        self.assertEqual(
            person.objects.all()._get_filter(~tldap.Q(uid='tux')),
            "(&(!(uid=tux)))")
        self.assertEqual(
            person.objects.all()._get_filter(tldap.Q(uid='tux') | tldap.Q(uid='tuz')),
            "(|(uid=tux)(uid=tuz))")
        self.assertEqual(
            person.objects.all()._get_filter(tldap.Q(uid='tux') & tldap.Q(uid='tuz')),
            "(&(uid=tux)(uid=tuz))")
        self.assertEqual(
            person.objects.all()._get_filter(tldap.Q(uid='tux') & ( tldap.Q(uid='tuz') | tldap.Q(uid='meow'))),
            "(&(uid=tux)(|(uid=tuz)(uid=meow)))")

        r = person.objects.filter(tldap.Q(uid='tux') | tldap.Q(uid='tuz'))
        self.assertEqual(len(r), 2)

        self.assertRaises(person.MultipleObjectsReturned, person.objects.get, tldap.Q(uid='tux') | tldap.Q(uid='tuz'))
        person.objects.get(~tldap.Q(uid='tuz'))

        r = g1.users.all()
        self.assertEqual(len(r), 1)

        r = g2.users.all()
        self.assertEqual(len(r), 2)

        r = p1.groups.all()
        self.assertEqual(len(r), 2)

        r = p2.groups.all()
        self.assertEqual(len(r), 1)

if __name__ == '__main__':
    unittest.main()
