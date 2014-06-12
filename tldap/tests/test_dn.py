#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Copyright 2012-2014 VPAC
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

import unittest
import tldap.dn


class DNTest(unittest.TestCase):

    def test_rfc4512_char(self):
        self.assertTrue(tldap.dn._isALPHA('A'))
        self.assertFalse(tldap.dn._isALPHA('0'))

    def test_rfc4512_number(self):
        value = "0"
        (result, i) = tldap.dn._number(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, value)
        self.assertEquals(i, len(value))

        value = "10"
        (result, i) = tldap.dn._number(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, value)
        self.assertEquals(i, len(value))

        value = "1a"
        (result, i) = tldap.dn._number(value, 0)
        self.assertIsNotNone(result)
        value = "1"
        self.assertEquals(result, value)
        self.assertEquals(i, len(value))

        value = ""
        (result, i) = tldap.dn._number(value, 0)
        self.assertIsNone(result)
        self.assertEquals(i, 0)

    def test_rfc4512_keystring(self):
        value = "A0b-d"
        (result, i) = tldap.dn._keystring(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, value)
        self.assertEquals(i, len(value))

        value = "A0b-d="
        (result, i) = tldap.dn._keystring(value, 0)
        self.assertIsNotNone(result)
        value = value[:-1]
        self.assertEquals(result, value)
        self.assertEquals(i, len(value))

        value = "A"
        (result, i) = tldap.dn._keystring(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, value)
        self.assertEquals(i, len(value))

        value = "O"
        (result, i) = tldap.dn._keystring(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, value)
        self.assertEquals(i, len(value))

        value = "O="
        (result, i) = tldap.dn._keystring(value, 0)
        self.assertIsNotNone(result)
        value = "O"
        self.assertEquals(result, value)
        self.assertEquals(i, len(value))

        value = "0b-d"
        (result, i) = tldap.dn._keystring(value, 0)
        self.assertIsNone(result)
        self.assertEquals(i, 0)

    def test_rfc4514_attributeType(self):
        value = "A0b-d"
        (result, i) = tldap.dn._attributeType(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, value)
        self.assertEquals(i, len(value))

        value = "A0b-d="
        (result, i) = tldap.dn._attributeType(value, 0)
        self.assertIsNotNone(result)
        value = value[:-1]
        self.assertEquals(result, value)
        self.assertEquals(i, len(value))

        value = "O"
        (result, i) = tldap.dn._attributeType(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, value)
        self.assertEquals(i, len(value))

        value = "O="
        (result, i) = tldap.dn._attributeType(value, 0)
        self.assertIsNotNone(result)
        value = "O"
        self.assertEquals(result, value)
        self.assertEquals(i, len(value))

        value = "0b-d"
        (result, i) = tldap.dn._attributeType(value, 0)
        self.assertIsNotNone(result)
        value = "0"
        self.assertEquals(result, value)
        self.assertEquals(i, len(value))

        value = "1.3.6.1.4.1.1466.0"
        (result, i) = tldap.dn._attributeType(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, value)
        self.assertEquals(i, len(value))

    def test_rfc4514_string(self):
        value = "AD"
        (result, i) = tldap.dn._string(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, value)
        self.assertEquals(i, len(value))

        value = "ABCD"
        (result, i) = tldap.dn._string(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, value)
        self.assertEquals(i, len(value))

        value = "AD,"
        (result, i) = tldap.dn._string(value, 0)
        self.assertIsNotNone(result)
        value = value[:-1]
        self.assertEquals(result, value)
        self.assertEquals(i, len(value))

        value = "ABCD,"
        (result, i) = tldap.dn._string(value, 0)
        self.assertIsNotNone(result)
        value = value[:-1]
        self.assertEquals(result, value)
        self.assertEquals(i, len(value))

        value = "\\\\a\\ \\#\\=\\+\\,\\;\\<\\>\\41"
        (result, i) = tldap.dn._string(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, "\\a #=+,;<>A")
        self.assertEquals(i, len(value))

    def test_rfc4514_attributeValue(self):
        value = "AD"
        (result, i) = tldap.dn._attributeValue(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, value)
        self.assertEquals(i, len(value))

        value = "ABCD"
        (result, i) = tldap.dn._attributeValue(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, value)
        self.assertEquals(i, len(value))

        value = "AD,"
        (result, i) = tldap.dn._attributeValue(value, 0)
        self.assertIsNotNone(result)
        value = value[:-1]
        self.assertEquals(result, value)
        self.assertEquals(i, len(value))

        value = "ABCD,"
        (result, i) = tldap.dn._attributeValue(value, 0)
        self.assertIsNotNone(result)
        value = value[:-1]
        self.assertEquals(result, value)
        self.assertEquals(i, len(value))

        value = "\\\\a\\ \\#\\=\\+\\,\\;\\<\\>\\41"
        (result, i) = tldap.dn._attributeValue(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, "\\a #=+,;<>A")
        self.assertEquals(i, len(value))

        value = "#414243"
        (result, i) = tldap.dn._attributeValue(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, "ABC")
        self.assertEquals(i, len(value))

        value = "#"
        (result, i) = tldap.dn._attributeValue(value, 0)
        self.assertIsNone(result)
        self.assertEquals(i, 0)

    def test_rfc4514_attributeTypeAndValue(self):
        value = "ABC=DEF"
        (result, i) = tldap.dn._attributeTypeAndValue(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, ("ABC", "DEF", 1))
        self.assertEquals(i, len(value))

        value = "O=Isode Limited"
        (result, i) = tldap.dn._attributeTypeAndValue(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, ("O", "Isode Limited", 1))
        self.assertEquals(i, len(value))

    def test_rfc4514_relativeDistinguishedName(self):
        value = "ABC=DEF"
        (result, i) = tldap.dn._relativeDistinguishedName(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, [("ABC", "DEF", 1)])
        self.assertEquals(i, len(value))

        value = "ABC=DEF+HIJ=KIF"
        (result, i) = tldap.dn._relativeDistinguishedName(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, [("ABC", "DEF", 1), ("HIJ", "KIF", 1)])
        self.assertEquals(i, len(value))

        value = "ABC=DEF,HIJ=KIF"
        (result, i) = tldap.dn._relativeDistinguishedName(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, [("ABC", "DEF", 1)])
        self.assertEquals(i, len("ABC=DEF"))

    def test_rfc4514_distinguishedName(self):
        value = "ABC=DEF,HIJ=KIF"
        (result, i) = tldap.dn._distinguishedName(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, [[('ABC', 'DEF', 1)], [('HIJ', 'KIF', 1)]])
        self.assertEquals(i, len(value))

    def test_str2dn(self):
#        value = "ABC=DEF,HIJ=KIF£"
#        result = tldap.dn.str2dn(value, 0)
#        self.assertIsNotNone(result)
#        self.assertEquals(result, [[('ABC', 'DEF', 1)], [('HIJ', 'KIF£', 1)]])

        value = "ABC=DEF,HIJ=KIF\\"
        self.assertRaises(
            tldap.exceptions.InvalidDN, lambda: tldap.dn.str2dn(value, 0))

        value = "CN=Steve Kille,O=Isode Limited,C=GB"
        result = tldap.dn.str2dn(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, [
            [('CN', 'Steve Kille', 1)],
            [('O', 'Isode Limited', 1)],
            [('C', 'GB', 1)],
        ])

        value = "OU=Sales+CN=J. Smith,O=Widget Inc.,C=US"
        result = tldap.dn.str2dn(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, [
            [('OU', 'Sales', 1), ('CN', 'J. Smith', 1)],
            [('O', 'Widget Inc.', 1)],
            [('C', 'US', 1)],
        ])

        value = "CN=L. Eagle,O=Sue\, Grabbit and Runn,C=GB"
        result = tldap.dn.str2dn(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, [
            [('CN', 'L. Eagle', 1)],
            [('O', 'Sue, Grabbit and Runn', 1)],
            [('C', 'GB', 1)],
        ])

        value = "CN=Before\\0DAfter,O=Test,C=GB"
        result = tldap.dn.str2dn(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, [
            [('CN', 'Before\rAfter', 1)],
            [('O', 'Test', 1)],
            [('C', 'GB', 1)],
        ])

        value = "1.3.6.1.4.1.1466.0=#04024869,O=Test,C=GB"
        result = tldap.dn.str2dn(value, 0)
        self.assertIsNotNone(result)
        self.assertEquals(result, [
            [('1.3.6.1.4.1.1466.0', '\x04\x02Hi', 1)],
            [('O', 'Test', 1)],
            [('C', 'GB', 1)],
        ])
