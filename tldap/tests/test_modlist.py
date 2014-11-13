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

import unittest
import ldap3
from distutils.version import LooseVersion

import tldap.modlist


class DNTest(unittest.TestCase):

    def test_addModlist(self):
        A = {
            'A': ['ABC'],
            'B': ['DEF'],
        }
        if LooseVersion(getattr(ldap3, '__version__', "0")) \
                < LooseVersion("0.9.6"):
            EXPECTED = {
                'A': ['\\41\\42\\43'],
                'B': ['\\44\\45\\46'],
            }
        else:
            EXPECTED = {
                'A': ['ABC'],
                'B': ['DEF'],
            }
        modlist = tldap.modlist.addModlist(A)
        self.assertEqual(modlist, EXPECTED)

    def test_modifyModlist(self):
        A = {
            'A': ['ABC'],
            'B': ['DEF'],
            'I': [''],
            'X': ['AA', 'BB', 'CC'],
            'Y': ['AA', 'BB', 'DD'],
        }
        B = {
            'A': ['ABC'],
            'C': ['HIJ'],
            'I': [''],
            'X': ['CC', 'BB', 'AA'],
            'Y': ['CC', 'BB', 'AA'],
        }
        if LooseVersion(getattr(ldap3, '__version__', "0")) \
                < LooseVersion("0.9.6"):
            EXPECTED = {
                'B': (ldap3.MODIFY_DELETE, []),
                'C': (ldap3.MODIFY_ADD, ['\\48\\49\\4a']),
                'Y': (ldap3.MODIFY_REPLACE, [
                    '\\43\\43', '\\42\\42', '\\41\\41']),
            }
        else:
            EXPECTED = {
                'B': (ldap3.MODIFY_DELETE, []),
                'C': (ldap3.MODIFY_ADD, ['HIJ']),
                'Y': (ldap3.MODIFY_REPLACE, ['CC', 'BB', 'AA']),
            }
        modlist = tldap.modlist.modifyModlist(A, B)
        self.assertEqual(modlist, EXPECTED)
