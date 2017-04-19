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

""" This module provides the LDAP base functions
with a subset of the functions from the real ldap module. """

import ssl
import ldap3
import ldap3.core.exceptions as exceptions
import logging
from ..compat import SIMPLE

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

logger = logging.getLogger(__name__)


def _debug(*argv):
    argv = [str(arg) for arg in argv]
    logger.debug(" ".join(argv))


class LDAPbase(object):
    """ The vase LDAP connection class. """

    def __init__(self, settings_dict):
        self.settings_dict = settings_dict
        self._obj = None

    def reset(self):
        pass

    def close(self):
        if self._obj is not None:
            self._obj.unbind()
            self._obj = None

    #########################
    # Connection Management #
    #########################

    def check_password(self, dn, password):
        try:
            conn = self._connect(user=dn, password=password)
            conn.unbind()
            return True
        except exceptions.LDAPInvalidCredentialsResult:
            return False

    def _connect(self, user, password):
        settings = self.settings_dict

        _debug("connecting")
        url = urlparse(settings['URI'])

        if url.scheme == "ldaps":
            use_ssl = True
        elif url.scheme == "ldap":
            use_ssl = False
        else:
            raise RuntimeError("Unknown scheme '%s'" % url.scheme)

        if ":" in url.netloc:
            host, port = url.netloc.split(":")
            port = int(port)
        else:
            host = url.netloc
            if use_ssl:
                port = 636
            else:
                port = 389

        start_tls = False
        if 'START_TLS' in settings and settings['START_TLS']:
            start_tls = True

        tls = None
        if use_ssl or start_tls:
            tls = ldap3.Tls()
            if 'TLS_CA' in settings and settings['TLS_CA']:
                tls.ca_certs_file = settings['TLS_CA']

            if 'REQUIRE_TLS' in settings and settings['REQUIRE_TLS']:
                tls.validate = ssl.CERT_REQUIRED

        s = ldap3.Server(host, port=port, use_ssl=use_ssl, tls=tls)
        c = ldap3.Connection(
            s,  # client_strategy=ldap3.STRATEGY_SYNC_RESTARTABLE,
            user=user, password=password, authentication=SIMPLE)
        c.strategy.restartable_sleep_time = 0
        c.strategy.restartable_tries = 1
        c.raise_exceptions = True

        c.open()

        if start_tls:
            c.start_tls()

        try:
            c.bind()
        except:
            c.unbind()
            raise

        return c

    def _reconnect(self):
        settings = self.settings_dict
        try:
            self._obj = self._connect(
                user=settings['USER'], password=settings['PASSWORD'])
        except Exception:
            self._obj = None
            raise
        assert self._obj is not None

    def _do_with_retry(self, fn):
        if self._obj is None:
            self._reconnect()
            assert self._obj is not None

        try:
            return fn(self._obj)
        except ldap3.core.exceptions.LDAPSessionTerminatedByServerError:
            # if it fails, reconnect then retry
            _debug("SERVER_DOWN, reconnecting")
            self._reconnect()
            return fn(self._obj)

    ###################
    # read only stuff #
    ###################

    def search(self, base, scope, filterstr='(objectClass=*)',
               attrlist=None, limit=None):
        """
        Search for entries in LDAP database.
        """

        _debug("search", base, scope, filterstr, attrlist, limit)

        # first results
        if attrlist is None:
            attrlist = ldap3.ALL_ATTRIBUTES
        elif isinstance(attrlist, set):
            attrlist = list(attrlist)

        def first_results(obj):
            _debug("---> searching ldap", limit)
            obj.search(
                base, filterstr, scope, attributes=attrlist, paged_size=limit)
            return obj.response

        # get the 1st result
        result_list = self._do_with_retry(first_results)

        # Loop over list of search results
        for result_item in result_list:
            # skip searchResRef for now
            if result_item['type'] != "searchResEntry":
                continue
            dn = result_item['dn']
            attributes = result_item['raw_attributes']
            # did we already retrieve this from cache?
            _debug("---> got ldap result", dn)
            _debug("---> yielding", result_item)
            yield (dn, attributes)

        # we are finished - return results, eat cake
        _debug("---> done")
        return
