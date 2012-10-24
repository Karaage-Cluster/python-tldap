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

import ldap

# hardcoded settings for this module

debugging = False
delayed_connect = True

# debugging

def debug(*argv):
    argv = [ str(arg) for arg in argv ]
    if debugging:
        print " ".join(argv)

# wrapper class

class LDAPwrapper(object):

    def __init__(self, settings_dict):
        self.settings_dict = settings_dict
        self._obj = None

        if not delayed_connect:
            self._reconnect()


    def check_password(self, dn, password):
        s = self.settings_dict
        l = ldap.initialize(s['URI'])
        try:
            l.simple_bind_s(dn, password)
            return True
        except ldap.INVALID_CREDENTIALS:
            return False
        return True


    #########################
    # Connection Management #
    #########################

    def _reconnect(self):
        s = self.settings_dict

        debug("connecting")
        conn = ldap.initialize(s['URI'])
        conn.protocol_version = ldap.VERSION3

        if s['USE_TLS']:
            ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, s['TLS_CA'])
            conn.set_option(ldap.OPT_X_TLS, ldap.OPT_X_TLS_DEMAND)
            conn.start_tls_s()

        self._obj = conn

        if s['USER'] is not None:
            debug("binding")
            self._obj.simple_bind_s(s['USER'], s['PASSWORD'])


    def _do_with_retry(self, fn):
        # if no connection
        if self._obj is None:
            # never connected; try to connect and then run fn
            debug("initial connection")
            self._reconnect()
            return fn(self._obj)

        # otherwise try to run fn
        try:
            return fn(self._obj)
        except ldap.SERVER_DOWN:
            # if it fails, reconnect then retry
            debug("SERVER_DOWN, reconnecting")
            self._reconnect()
            return fn(self._obj)

    ####################
    # Cache Management #
    ####################

    def reset(self, forceflushcache=False):
        """ Reset transaction back to original state, discarding all uncompleted transactions. """
        pass

    ##########################
    # Transaction Management #
    ##########################

    # Fake it

    def is_dirty(self):
        """ Are there uncommitted changes? """
        return False

    def is_managed(self):
        """ Are we inside transaction management? """
        return False

    def enter_transaction_management(self):
        """ Start a transaction. """
        pass

    def leave_transaction_management(self):
        """ End a transaction. Must not be dirty when doing so. ie. commit() or
        rollback() must be called if changes made. If dirty, changes will be discarded. """
        pass

    def commit(self):
        pass

    def rollback(self):
        pass

    ##################################
    # Functions needing Transactions #
    ##################################

    def add(self, dn, modlist, onfailure=None):
        return self._do_with_retry(lambda obj: obj.add_s(dn, modlist))


    def modify(self, dn, modlist, onfailure=None):
        return self._do_with_retry(lambda obj: obj.modify_s(dn, modlist))

    def delete(self, dn, onfailure=None):
        return self._do_with_retry(lambda obj: obj.delete_s(dn))

    def rename(self, dn, newrdn, onfailure=None):
        return self._do_with_retry(lambda obj: obj.rename_s(dn, newrdn))

    def search(self, base, scope, *args, **kwargs):
        return self._do_with_retry(lambda obj: obj.search_s(base, scope, *args, **kwargs))

    #######################
    # Compatability Hacks #
    #######################

    def add_s(self, *args, **kwargs):
        return self.add(*args, **kwargs)

    def modify_s(self, *args, **kwargs):
        return self.modify(*args, **kwargs)

    def delete_s(self, *args, **kwargs):
        return self.delete(*args, **kwargs)

    def rename_s(self, *args, **kwargs):
        return self.rename(*args, **kwargs)

    def search_s(self, *args, **kwargs):
        return self.search(*args, **kwargs)

