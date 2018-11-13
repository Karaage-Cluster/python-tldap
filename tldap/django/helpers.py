# Copyright 2018 Brian May
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
from tldap.database import LdapObject, LdapChanges
from tldap.database.helpers import get_value
from tldap.django.models import Counters


def save_account(changes: LdapChanges, settings: dict) -> LdapChanges:
    d = {}

    uid_number = get_value(changes, 'uidNumber')
    if uid_number is None:
        scheme = settings.get('NUMBER_SCHEME')
        first = settings.get('UID_FIRST', 10000)
        d['uidNumber'] = Counters.get_and_increment(
            scheme, "uidNumber", first,
            lambda n: True  # FIXME
        )

    changes = changes.merge(d)
    return changes


def save_group(changes: LdapChanges, settings: dict) -> LdapChanges:
    d = {}

    gid_number = get_value(changes, 'gidNumber')
    if gid_number is None:
        scheme = settings.get('NUMBER_SCHEME')
        first = settings.get('GID_FIRST', 10000)
        d['gidNumber'] = Counters.get_and_increment(
            scheme, "gidNumber", first,
            lambda n: True  # FIXME
        )

    changes = changes.merge(d)
    return changes
