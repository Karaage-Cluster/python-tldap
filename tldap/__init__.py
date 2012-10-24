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

import tldap.utils
from tldap.query_utils import Q
from tldap.utils import DEFAULT_LDAP_ALIAS

connections = None
connection = None

def _configure_django():
    # Try to use django settings
    from django.conf import settings

    # For backwards compatibility - Port any old database settings over to
    # the new values.
    if not hasattr(settings, 'LDAP'):
        settings.LDAP = {}

    # ok to use django settings
    if not settings.LDAP:
        settings.LDAP[DEFAULT_LDAP_ALIAS] = {
            'ENGINE': 'tldap.backend.transaction',
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

    global connections
    global connection

    if DEFAULT_LDAP_ALIAS not in settings.LDAP:
        raise RuntimeError("You must define a '%s' ldap database" % DEFAULT_LDAP_ALIAS)
    connections = tldap.utils.ConnectionHandler(settings.LDAP)
    connection = connections[DEFAULT_LDAP_ALIAS]

_configure_django()
