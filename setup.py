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

import sys

from setuptools import Command, setup, find_packages


VERSION='1.0.4'

class VerifyVersionCommand(Command):
    """Custom command to verify that the git tag matches our version"""
    description = 'verify that the git tag matches our version'
    user_options = [
      ('version=', None, 'expected version'),
    ]

    def initialize_options(self):
        self.version = None

    def finalize_options(self):
        pass

    def run(self):
        version = self.version

        if version != VERSION:
            info = "{0} does not match the version of this app: {1}".format(
                version, VERSION
            )
            sys.exit(info)

setup(
    name="python-tldap",
    version=VERSION,
    url='https://github.com/Karaage-Cluster/python-tldap',
    author='Brian May',
    author_email='brian@linuxpenguins.xyz',
    description='High level python LDAP Library',
    packages=[
        'tldap', 'tldap.backend',
        'tldap.django', 'tldap.django.migrations',
        'tldap.database',
        'tldap.test', 'tldap.test.ldap_schemas',
    ],
    license="GPL3+",
    long_description=open('README.rst').read(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: "
            "GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
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
    cmdclass={
        'verify': VerifyVersionCommand,
    }
)
