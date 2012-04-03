# Copyright 2012 VPAC
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

from tldap.utils import DEFAULT_LDAP_ALIAS, ConnectionHandler

connections = None
connection = None

def configure(settings):
    global connections
    global connection

    if DEFAULT_LDAP_ALIAS not in settings:
        raise RuntimeError("You must define a '%s' ldap database" % DEFAULT_LDAP_ALIAS)
    connections = ConnectionHandler(settings)
    connection = connections[DEFAULT_LDAP_ALIAS]

import ldap
try:
    # Try to use django settings
    from django.conf import settings

    # For backwards compatibility - Port any old database settings over to
    # the new values.
    if not hasattr(settings, 'LDAP'):
        settings.LDAP = {}
except:
    # django can't be loaded, don't use django settings
    pass

else:
    # ok to use django settings
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

        configure(settings.LDAP)

# submodules from ldap
import ldap.modlist as modlist

# constants from ldap
MOD_ADD = ldap.MOD_ADD
MOD_DELETE = ldap.MOD_DELETE
MOD_REPLACE = ldap.MOD_REPLACE
SCOPE_BASE = ldap.SCOPE_BASE
SCOPE_ONELEVEL = ldap.SCOPE_ONELEVEL
SCOPE_SUBTREE = ldap.SCOPE_SUBTREE
PROTOCOL_ERROR = ldap.PROTOCOL_ERROR

LDAPError = ldap.LDAPError
ALREADY_EXISTS = ldap.ALREADY_EXISTS
NO_RESULTS_RETURNED = ldap.NO_RESULTS_RETURNED
NO_SUCH_OBJECT = ldap.NO_SUCH_OBJECT
TYPE_OR_VALUE_EXISTS = ldap.TYPE_OR_VALUE_EXISTS
NO_SUCH_ATTRIBUTE = ldap.NO_SUCH_ATTRIBUTE
