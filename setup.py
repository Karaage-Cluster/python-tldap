#!/usr/bin/env python

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

from setuptools import setup, find_packages

with open('VERSION.txt', 'r') as f:
    version = f.readline().strip()

setup(
    name = "django-tldap",
    version = version,
    author = 'Brian May',
    author_email = 'brian@microcomaustralia.com.au',
    description = 'High level python LDAP Library',
    license = "GPL3+",
    packages = find_packages() + [ 'tldap.test.ldap_schemas' ],
    package_data = {
        'tldap.test.ldap_schemas': [ '*.schema', ],
    },
    url = "https://github.com/Karaage-Cluster/django-tldap",
    install_requires = [
        "django",
        "python-ldap",
    ]
)
