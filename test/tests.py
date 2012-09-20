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

        # test roll back on exception
        try:
            with tldap.transaction.commit_on_success():
                c.add("uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
                c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "sn", "Gates") ])
                raise RuntimeError("testing failure")
        except RuntimeError:
            pass
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tux, ou=People, dc=python-ldap,dc=org")

        # test success commits
        with tldap.transaction.commit_on_success():
            c.add("uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "sn", "Gates") ])
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [ "Gates" ])
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "000" ])

        # test deleting attribute *of new object* with rollback
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_DELETE, "telephoneNumber", None) ])
            self.assertRaises(KeyError, lambda: self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'])
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "000" ])

        # test deleting attribute *of new object* with success
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_DELETE, "telephoneNumber", None) ])
            self.assertRaises(KeyError, lambda: self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'])
        self.assertRaises(KeyError, lambda: self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'])

        # test adding attribute with rollback
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_ADD, "telephoneNumber", "111") ])
            self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "111" ])
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertRaises(KeyError, lambda: self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'])

        # test adding attribute with success
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_ADD, "telephoneNumber", "111") ])
            self.assertRaises(ldap.TYPE_OR_VALUE_EXISTS, c.modify, "uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_ADD, "telephoneNumber", "111") ])
            self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "111" ])
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "111" ])

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

        r = c.search("uid=tux, ou=People, dc=python-ldap,dc=org", ldap.SCOPE_ONELEVEL, "uid=tux")
        self.assertEqual(len(r), 1)
        r = c.search("ou=People, dc=python-ldap,dc=org", ldap.SCOPE_ONELEVEL, "uid=tux")
        self.assertEqual(len(r), 1)
        r = c.search("dc=python-ldap,dc=org", ldap.SCOPE_ONELEVEL, "uid=tux")
        self.assertEqual(len(r), 0)
        r = c.search("ou=Groups, dc=python-ldap,dc=org", ldap.SCOPE_ONELEVEL, "uid=tux")
        self.assertEqual(len(r), 0)
        self.assertRaises(ldap.NO_SUCH_OBJECT, c.search, "dc=python,dc=org", ldap.SCOPE_BASE, "uid=tux")

        r = c.search("uid=tux, ou=People, dc=python-ldap,dc=org", ldap.SCOPE_SUBTREE, "uid=tux")
        self.assertEqual(len(r), 1)
        r = c.search("ou=People, dc=python-ldap,dc=org", ldap.SCOPE_SUBTREE, "uid=tux")
        self.assertEqual(len(r), 1)
        r = c.search("dc=python-ldap,dc=org", ldap.SCOPE_SUBTREE, "uid=tux")
        self.assertEqual(len(r), 1)
        r = c.search("ou=Groups, dc=python-ldap,dc=org", ldap.SCOPE_SUBTREE, "uid=tux")
        self.assertEqual(len(r), 0)
        self.assertRaises(ldap.NO_SUCH_OBJECT, c.search, "dc=python,dc=org", ldap.SCOPE_BASE, "uid=tux")

        # test replacing attribute with rollback
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "telephoneNumber", "222") ])
            self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "222" ])
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "111" ])

        # test replacing attribute with success
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "telephoneNumber", "222") ])
            self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "222" ])
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "222" ])

        # test deleting attribute value with rollback
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_DELETE, "telephoneNumber", "222") ])
            self.assertRaises(KeyError, lambda: self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'])
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "222" ])

        # test deleting attribute value with success
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_DELETE, "telephoneNumber", "222") ])
            self.assertRaises(ldap.NO_SUCH_ATTRIBUTE, c.modify, "uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_DELETE, "telephoneNumber", "222") ])
            self.assertRaises(KeyError, lambda: self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'])
        self.assertRaises(KeyError, lambda: self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'])

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

        # test rename with rollback
        with tldap.transaction.commit_on_success():
            c.rename("uid=tux, ou=People, dc=python-ldap,dc=org", 'uid=tuz')
            c.modify("uid=tuz, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "sn", "Tuz") ])
            self.assertEqual(self.get(c, "uid=tuz, ou=People, dc=python-ldap,dc=org")['sn'], [ "Tuz" ])
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [ "Gates" ])
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tuz, ou=People, dc=python-ldap,dc=org")

        # test rename with success
        with tldap.transaction.commit_on_success():
            c.rename("uid=tux, ou=People, dc=python-ldap,dc=org", 'uid=tuz')
            c.modify("uid=tuz, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "sn", "Tuz") ])
            self.assertEqual(self.get(c, "uid=tuz, ou=People, dc=python-ldap,dc=org")['sn'], [ "Tuz" ])
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(self.get(c, "uid=tuz, ou=People, dc=python-ldap,dc=org")['sn'], [ "Tuz" ])

        # test rename back with success
        with tldap.transaction.commit_on_success():
            c.modify("uid=tuz, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "sn", "Gates") ])
            c.rename("uid=tuz, ou=People, dc=python-ldap,dc=org", 'uid=tux')
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tuz, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [ "Gates" ])

        # test roll back on error of delete and add of same user
        with tldap.transaction.commit_on_success():
            c.delete("uid=tux, ou=People, dc=python-ldap,dc=org")
            self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tux, ou=People, dc=python-ldap,dc=org")
            c.add("uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
            self.assertRaises(ldap.ALREADY_EXISTS, c.add, "uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [ "Gates" ])

        # test delate and add same user
        with tldap.transaction.commit_on_success():
            c.delete("uid=tux, ou=People, dc=python-ldap,dc=org")
            self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tux, ou=People, dc=python-ldap,dc=org")
            c.add("uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [ "Torvalds" ])

        # test delate
        with tldap.transaction.commit_on_success():
            c.delete("uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tux, ou=People, dc=python-ldap,dc=org")

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
        c = tldap.connection
        c.autoflushcache = False

        person = tldap.models.person
        DoesNotExist = person.DoesNotExist
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
        p = person(dn="ou=People, dc=python-ldap,dc=org", **kwargs)
        p.save()

        # test explicit roll back
        with tldap.transaction.commit_on_success():
            p = create(dn="uid=tux, ou=People, dc=python-ldap,dc=org", **kwargs)
            p.sn = "Gates"
            p.save()
            c.rollback()
        self.assertRaises(DoesNotExist, get, dn="uid=tux, ou=People, dc=python-ldap,dc=org")

        # test roll back on exception
        try:
            with tldap.transaction.commit_on_success():
                p = create(dn="uid=tux, ou=People, dc=python-ldap,dc=org", **kwargs)
                p.sn = "Gates"
                p.save()
                raise RuntimeError("testing failure")
        except RuntimeError:
            pass
        self.assertRaises(DoesNotExist, get, dn="uid=tux, ou=People, dc=python-ldap,dc=org")

        # test success commits
        with tldap.transaction.commit_on_success():
            p = create(dn="uid=tux, ou=People, dc=python-ldap,dc=org", **kwargs)
            p.sn = "Gates"
            p.save()
        self.assertEqual(get(dn="uid=tux, ou=People, dc=python-ldap,dc=org").sn, "Gates")
        self.assertEqual(get(dn="uid=tux, ou=People, dc=python-ldap,dc=org").telephoneNumber, "000")


        p, created = get_or_create(dn="uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(created, False)
        p.telephoneNumber = None

        # test deleting attribute *of new object* with rollback
        with tldap.transaction.commit_on_success():
            p.reload_db_values()
            p.save()
            self.assertEqual(get(dn="uid=tux, ou=People, dc=python-ldap,dc=org").telephoneNumber, None)
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertEqual(get(dn="uid=tux, ou=People, dc=python-ldap,dc=org").telephoneNumber, "000")

        # test deleting attribute *of new object* with success
        with tldap.transaction.commit_on_success():
            p.reload_db_values()
            p.save()
            self.assertEqual(get(dn="uid=tux, ou=People, dc=python-ldap,dc=org").telephoneNumber, None)
        self.assertEqual(get(dn="uid=tux, ou=People, dc=python-ldap,dc=org").telephoneNumber, None)

        return

        # test adding attribute with rollback
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_ADD, "telephoneNumber", "111") ])
            self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "111" ])
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertRaises(KeyError, lambda: self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'])

        # test adding attribute with success
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_ADD, "telephoneNumber", "111") ])
            self.assertRaises(ldap.TYPE_OR_VALUE_EXISTS, c.modify, "uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_ADD, "telephoneNumber", "111") ])
            self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "111" ])
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "111" ])

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

        r = c.search("uid=tux, ou=People, dc=python-ldap,dc=org", ldap.SCOPE_ONELEVEL, "uid=tux")
        self.assertEqual(len(r), 1)
        r = c.search("ou=People, dc=python-ldap,dc=org", ldap.SCOPE_ONELEVEL, "uid=tux")
        self.assertEqual(len(r), 1)
        r = c.search("dc=python-ldap,dc=org", ldap.SCOPE_ONELEVEL, "uid=tux")
        self.assertEqual(len(r), 0)
        r = c.search("ou=Groups, dc=python-ldap,dc=org", ldap.SCOPE_ONELEVEL, "uid=tux")
        self.assertEqual(len(r), 0)
        self.assertRaises(ldap.NO_SUCH_OBJECT, c.search, "dc=python,dc=org", ldap.SCOPE_BASE, "uid=tux")

        r = c.search("uid=tux, ou=People, dc=python-ldap,dc=org", ldap.SCOPE_SUBTREE, "uid=tux")
        self.assertEqual(len(r), 1)
        r = c.search("ou=People, dc=python-ldap,dc=org", ldap.SCOPE_SUBTREE, "uid=tux")
        self.assertEqual(len(r), 1)
        r = c.search("dc=python-ldap,dc=org", ldap.SCOPE_SUBTREE, "uid=tux")
        self.assertEqual(len(r), 1)
        r = c.search("ou=Groups, dc=python-ldap,dc=org", ldap.SCOPE_SUBTREE, "uid=tux")
        self.assertEqual(len(r), 0)
        self.assertRaises(ldap.NO_SUCH_OBJECT, c.search, "dc=python,dc=org", ldap.SCOPE_BASE, "uid=tux")

        # test replacing attribute with rollback
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "telephoneNumber", "222") ])
            self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "222" ])
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "111" ])

        # test replacing attribute with success
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "telephoneNumber", "222") ])
            self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "222" ])
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "222" ])

        # test deleting attribute value with rollback
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_DELETE, "telephoneNumber", "222") ])
            self.assertRaises(KeyError, lambda: self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'])
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'], [ "222" ])

        # test deleting attribute value with success
        with tldap.transaction.commit_on_success():
            c.modify("uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_DELETE, "telephoneNumber", "222") ])
            self.assertRaises(ldap.NO_SUCH_ATTRIBUTE, c.modify, "uid=tux, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_DELETE, "telephoneNumber", "222") ])
            self.assertRaises(KeyError, lambda: self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'])
        self.assertRaises(KeyError, lambda: self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['telephoneNumber'])

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

        # test rename with rollback
        with tldap.transaction.commit_on_success():
            c.rename("uid=tux, ou=People, dc=python-ldap,dc=org", 'uid=tuz')
            c.modify("uid=tuz, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "sn", "Tuz") ])
            self.assertEqual(self.get(c, "uid=tuz, ou=People, dc=python-ldap,dc=org")['sn'], [ "Tuz" ])
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [ "Gates" ])
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tuz, ou=People, dc=python-ldap,dc=org")

        # test rename with success
        with tldap.transaction.commit_on_success():
            c.rename("uid=tux, ou=People, dc=python-ldap,dc=org", 'uid=tuz')
            c.modify("uid=tuz, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "sn", "Tuz") ])
            self.assertEqual(self.get(c, "uid=tuz, ou=People, dc=python-ldap,dc=org")['sn'], [ "Tuz" ])
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(self.get(c, "uid=tuz, ou=People, dc=python-ldap,dc=org")['sn'], [ "Tuz" ])

        # test rename back with success
        with tldap.transaction.commit_on_success():
            c.modify("uid=tuz, ou=People, dc=python-ldap,dc=org", [ (ldap.MOD_REPLACE, "sn", "Gates") ])
            c.rename("uid=tuz, ou=People, dc=python-ldap,dc=org", 'uid=tux')
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tuz, ou=People, dc=python-ldap,dc=org")
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [ "Gates" ])

        # test roll back on error of delete and add of same user
        with tldap.transaction.commit_on_success():
            c.delete("uid=tux, ou=People, dc=python-ldap,dc=org")
            self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tux, ou=People, dc=python-ldap,dc=org")
            c.add("uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
            self.assertRaises(ldap.ALREADY_EXISTS, c.add, "uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
            c.fail() # raises TestFailure during commit causing rollback
            self.assertRaises(tldap.exceptions.TestFailure, c.commit)
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [ "Gates" ])

        # test delate and add same user
        with tldap.transaction.commit_on_success():
            c.delete("uid=tux, ou=People, dc=python-ldap,dc=org")
            self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tux, ou=People, dc=python-ldap,dc=org")
            c.add("uid=tux, ou=People, dc=python-ldap,dc=org", modlist)
        self.assertEqual(self.get(c, "uid=tux, ou=People, dc=python-ldap,dc=org")['sn'], [ "Torvalds" ])

        # test delate
        with tldap.transaction.commit_on_success():
            c.delete("uid=tux, ou=People, dc=python-ldap,dc=org")
        self.assertRaises(ldap.NO_SUCH_OBJECT, self.get, c, "uid=tux, ou=People, dc=python-ldap,dc=org")

        c.autoflushcache = True

if __name__ == '__main__':
    unittest.main()
