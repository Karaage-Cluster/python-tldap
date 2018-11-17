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
from setuptools import setup

setup(
    name="python-tldap",
    use_scm_version={
        'write_to': "tldap/version.py",
    },
    setup_requires=['setuptools_scm'],
    url='https://github.com/Karaage-Cluster/python-tldap',
    author='Brian May',
    author_email='brian@linuxpenguins.xyz',
    description='High level python LDAP Library',
    packages=[
        'tldap', 'tldap.backend',
        'tldap.database',
        'tldap.test', 'tldap.test.ldap_schemas',
    ],
    license="GPL3+",
    long_description=open('README.rst').read(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: "
            "GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.6",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="ldap",
    package_data={
        'tldap.test.ldap_schemas': ['*.schema', ],
    },
    install_requires=[
        "ldap3",
        "passlib",
        "six",
    ],
    tests_require=[
        "pytest",
        "pytest-runner",
    ],
)
