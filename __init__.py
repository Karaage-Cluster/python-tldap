# Copyright 2012 VPAC
#
# This file is part of django-placard.
#
# django-placard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# django-placard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with django-placard  If not, see <http://www.gnu.org/licenses/>.

from placard.tldap.utils import DEFAULT_LDAP_ALIAS, ConnectionHandler

import ldap
from django.conf import settings

# For backwards compatibility - Port any old database settings over to
# the new values.
if not hasattr(settings, 'LDAP'):
    settings.LDAP = {}

if not settings.LDAP:
    settings.LDAP[DEFAULT_LDAP_ALIAS] = {
        'URI': settings.LDAP_URL,
        'USER': settings.LDAP_ADMIN_USER,
        'PASSWORD': settings.LDAP_ADMIN_PASSWORD,
        'USE_TLS' : False,
        'TLS_CA' : None,
    }
    if hasattr(settings, 'LDAP_USE_TLS'):
        settings.LDAP[DEFAULT_LDAP_ALIAS]["USE_TLS"] = settings.LDAP_USE_TLS
    if settings.LDAP[DEFAULT_LDAP_ALIAS]["USE_TLS"]:
        settings.LDAP[DEFAULT_LDAP_ALIAS]["TLS_CA"] = settings.LDAP_TLS_CA

if DEFAULT_LDAP_ALIAS not in settings.LDAP:
    raise RuntimeError("You must define a '%s' ldap database" % DEFAULT_LDAP_ALIAS)

connections = ConnectionHandler(settings.LDAP)
connection = connections[DEFAULT_LDAP_ALIAS]

# constants from ldap
MOD_ADD = ldap.MOD_ADD
MOD_DELETE = ldap.MOD_DELETE
MOD_REPLACE = ldap.MOD_REPLACE
SCOPE_ONELEVEL = ldap.SCOPE_ONELEVEL
SCOPE_SUBTREE = ldap.SCOPE_SUBTREE
PROTOCOL_ERROR = ldap.PROTOCOL_ERROR
