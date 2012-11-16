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

debugging = True
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
        """ Attempt to commit all changes to LDAP database, NOW! However stay inside transaction management. """
        pass

    def rollback(self):
        """ Roll back to previous database state. However stay inside transaction management. """
        pass

    ##################################
    # Functions needing Transactions #
    ##################################

    def add(self, dn, modlist, onfailure=None):
        """ Add a DN to the LDAP database; See ldap module. Doesn't return a
        return self._do_with_retry(lambda obj: obj.add_s(dn, modlist))


    def modify(self, dn, modlist, onfailure=None):
        """ Modify a DN in the LDAP database; See ldap module. Doesn't return a
        result if transactions enabled. """
        return self._do_with_retry(lambda obj: obj.modify_s(dn, modlist))

    def delete(self, dn, onfailure=None):
        """ delete a dn in the ldap database; see ldap module. doesn't return a
        return self._do_with_retry(lambda obj: obj.delete_s(dn))

    def rename(self, dn, newrdn, onfailure=None):
        """ rename a dn in the ldap database; see ldap module. doesn't return a
        result if transactions enabled. """
        return self._do_with_retry(lambda obj: obj.rename_s(dn, newrdn))

    # read only stuff

    def search(self, base, scope, filterstr='(objectClass=*)', attrlist=None, skip=0, limit=None):
        """ Search for entries in LDAP database. """

        # connect to ldap server
        if self._obj is None:
            # never connected; try to connect and then run fn
            debug("initial connection")
            self._reconnect()

        # do the real ldap search
        if isinstance(attrlist, set):
            attrlist = list(attrlist)
        msgid = self._obj.search_ext(base, scope, filterstr, attrlist, sizelimit=limit or 0)

        # get the 1st result
        try:
            result_type,result_list,result_msgid,result_serverctrls = self._obj.result3(msgid, 0)
        except ldap.SERVER_DOWN:
            # if it fails, reconnect then retry
            debug("SERVER_DOWN, reconnecting")
            self._reconnect()
            msgid = self._obj.search_ext(base, scope, filterstr, attrlist, sizelimit=limit or 0)
            result_type,result_list,result_msgid,result_serverctrls = self._obj.result3(msgid, 0)

        # get the next results
        while result_type and result_list:
            # Loop over list of search results
            for result_item in result_list:
                yield result_item
            result_type,result_list,result_msgid,result_serverctrls = self._obj.result3(msgid, 0)

        # we are finished - return results, eat cake
        return
