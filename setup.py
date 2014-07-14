#!/usr/bin/env python

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

import os
from setuptools import setup, find_packages

with open('VERSION.txt', 'r') as f:
    version = f.readline().strip()

os.environ['DJANGO_SETTINGS_MODULE'] = 'tldap.tests.settings'

setup(
    name="python-tldap",
    version=version,
    url='https://github.com/Karaage-Cluster/python-tldap',
    author='Brian May',
    author_email='brian@v3.org.au',
    description='High level python LDAP Library',
    packages=find_packages() + ['tldap.test.ldap_schemas'],
    license="GPL3+",
    long_description=open('README.rst').read(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Lesser General Public "
            "License v3 or later (LGPLv3+)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="ldap django",
    package_data={
        'tldap.test.ldap_schemas': ['*.schema', ],
    },
    install_requires=[
        "django",
        "python3-ldap",
        "passlib",
        "six",
    ],
    test_suite="tldap.tests",
)
