# Copyright 20012-2014 VPAC
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

""" This module provides the LDAP functions with transaction support faked,
with a subset of the functions from the real ldap module. """

import ldap
import ldap.dn
import tldap.exceptions
import sys

# hardcoded settings for this module

debugging = False
delayed_connect = True

# debugging


def debug(*argv):
    argv = [str(arg) for arg in argv]
    if debugging:
        print " ".join(argv)


def raise_testfailure(place):
    raise tldap.exceptions.TestFailure("fail %s called" % place)


# wrapper class

class LDAPwrapper(object):
    """ The LDAP connection class. """

    def __init__(self, settings_dict):
        self.settings_dict = settings_dict
        self._transact = False
        self._obj = None

        self._onrollback = None
        self._bind_args = None
        self._bind_kwargs = None

        self.reset()

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
        self._obj = None

        debug("connecting")
        conn = ldap.initialize(s['URI'])
        conn.protocol_version = ldap.VERSION3

        if s['USE_TLS']:
            ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, s['TLS_CA'])
            conn.set_option(ldap.OPT_X_TLS, ldap.OPT_X_TLS_DEMAND)
            conn.start_tls_s()

        if s['USER'] is not None:
            debug("binding")
            conn.simple_bind_s(s['USER'], s['PASSWORD'])

        self._obj = conn

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

    def reset(self):
        """
        Reset transaction back to original state, discarding all
        uncompleted transactions.
        """
        self._onrollback = []

    def _cache_normalize_dn(self, dn):
        """
        normalize the dn, i.e. remove unwanted white space - hopefully this
        will mean it is not possible to have two or more cache entries
        representing the same ldap entry.
        """
        return ldap.dn.dn2str(ldap.dn.str2dn(dn))

    def _cache_get_for_dn(self, dn):
        """
        Object state is cached. When an update is required the update will be
        simulated on this cache, so that rollback information can be correct.
        This function retrieves the cached data.
        """
        dn = self._cache_normalize_dn(dn).lower()

        # no cached item, retrieve from ldap
        results = self._do_with_retry(
            lambda obj: obj.search_s(
                dn, ldap.SCOPE_BASE, '(objectclass=*)', ['*', '+']))
        if len(results) < 1:
            raise ldap.NO_SUCH_OBJECT("No results finding current value")
        if len(results) > 1:
            raise RuntimeError("Too many results finding current value")
        return results[0]

    ##########################
    # Transaction Management #
    ##########################

    def is_dirty(self):
        """ Are there uncommitted changes? """
        if len(self._onrollback) > 0:
            return True
        return False

    def is_managed(self):
        """ Are we inside transaction management? """
        return self._transact

    def enter_transaction_management(self):
        """ Start a transaction. """
        if self._transact:
            raise RuntimeError(
                "enter_transaction_management called inside transaction")

        self._transact = True
        self._onrollback = []

    def leave_transaction_management(self):
        """
        End a transaction. Must not be dirty when doing so. ie. commit() or
        rollback() must be called if changes made. If dirty, changes will be
        discarded.
        """
        if not self._transact:
            self.reset()
            self._transact = False
            raise RuntimeError(
                "leave_transaction_management called outside transaction")
        if len(self._onrollback) > 0:
            self.reset()
            self._transact = False
            raise RuntimeError(
                "leave_transaction_management called "
                "with uncommited rollbacks")
        self.reset()
        self._transact = False

    def commit(self):
        """
        Attempt to commit all changes to LDAP database. i.e. forget all
        rollbacks.  However stay inside transaction management.
        """
        if not self._transact:
            raise RuntimeError("commit called outside transaction")

        debug("\ncommit")
        self.reset()

    def rollback(self):
        """
        Roll back to previous database state. However stay inside transaction
        management.
        """
        if not self._transact:
            raise RuntimeError("rollback called outside transaction")

        debug("\nrollback:", self._onrollback)
        # if something goes wrong here, nothing we can do about it, leave
        # database as is.
        try:
            # for every rollback action ...
            for onrollback, onfailure in self._onrollback:
                # execute it
                debug("--> rolling back", onrollback)
                self._do_with_retry(onrollback)
                if onfailure is not None:
                    onfailure()

        except:
            debug("--> rollback failed")
            exc_class, exc, tb = sys.exc_info()
            new_exc = tldap.exceptions.RollbackError(
                "FATAL Unrecoverable rollback error: %r" % (exc))
            raise new_exc.__class__, new_exc, tb
        finally:
            # reset everything to clean state
            debug("--> rollback success")
            self.reset()

    def _process(self, oncommit, onrollback, onfailure):
        """
        Process action. oncommit is a callback to execute action, onrollback is
        a callback to execute if the oncommit() has been called and a rollback
        is required
        """

        debug("---> commiting", oncommit)
        result = self._do_with_retry(oncommit)

        if not self._transact:
            self.reset()
        else:
            # add statement to rollback log in case something goes wrong
            self._onrollback.insert(0, (onrollback, onfailure))

        return result

    ##################################
    # Functions needing Transactions #
    ##################################

    def add(self, dn, modlist, onfailure=None):
        """
        Add a DN to the LDAP database; See ldap module. Doesn't return a result
        if transactions enabled.
        """

        debug("\nadd", self, dn, modlist)

        # if rollback of add required, delete it
        oncommit = lambda obj: obj.add_s(dn, modlist)
        onrollback = lambda obj: obj.delete_s(dn)

        # process this action
        return self._process(oncommit, onrollback, onfailure)

    def modify(self, dn, modlist, onfailure=None):
        """
        Modify a DN in the LDAP database; See ldap module. Doesn't return a
        result if transactions enabled.
        """

        debug("\nmodify", self, dn, modlist)

        # need to work out how to reverse changes in modlist; result in revlist
        revlist = []

        # get the current cached attributes
        result = self._cache_get_for_dn(dn)[1]

        # find the how to reverse modlist (for rollback) and put result in
        # revlist. Also simulate actions on cache.
        for mod_op, mod_type, mod_vals in modlist:
            reverse = None
            if mod_type in result:
                debug("attribute cache:", result[mod_type])
            else:
                debug("attribute cache is empty")
            debug("attribute modify:", (mod_op, mod_type, mod_vals))

            if mod_vals is not None:
                if not isinstance(mod_vals, list):
                    mod_vals = [mod_vals]

            if mod_op == ldap.MOD_ADD:
                # reverse of MOD_ADD is MOD_DELETE
                reverse = (ldap.MOD_DELETE, mod_type, mod_vals)

            elif mod_op == ldap.MOD_DELETE and mod_vals is not None:
                # Reverse of MOD_DELETE is MOD_ADD, but only if value is given
                # if mod_vals is None, this means all values where deleted.
                reverse = (ldap.MOD_ADD, mod_type, mod_vals)

            elif mod_op == ldap.MOD_DELETE or mod_op == ldap.MOD_REPLACE:
                if mod_type in result:
                    # If MOD_DELETE with no values or MOD_REPLACE then we
                    # have to replace all attributes with cached state
                    reverse = (ldap.MOD_REPLACE, mod_type, result[mod_type])
                else:
                    # except if we have no cached state for this DN, in which
                    # case we delete it.
                    reverse = (ldap.MOD_DELETE, mod_type, None)

            else:
                raise RuntimeError("mod_op of %d not supported" % mod_op)

            debug("attribute reverse:", reverse)
            if mod_type in result:
                debug("attribute cache:", result[mod_type])
            else:
                debug("attribute cache is empty")

            revlist.insert(0, reverse)

        debug("--\n")

        # now the hard stuff is over, we get to the easy stuff
        oncommit = lambda obj: obj.modify_s(dn, modlist)
        onrollback = lambda obj: obj.modify_s(dn, revlist)
        return self._process(oncommit, onrollback, onfailure)

    def modify_no_rollback(self, dn, modlist):
        """
        Modify a DN in the LDAP database; See ldap module. Doesn't return a
        result if transactions enabled.
        """

        debug("\nmodify_no_rollback", self, dn, modlist)
        result = self._do_with_retry(lambda obj: obj.modify_s(dn, modlist))
        debug("--\n")

        return result

    def delete(self, dn, onfailure=None):
        """
        delete a dn in the ldap database; see ldap module. doesn't return a
        result if transactions enabled.
        """

        debug("\ndelete", self)

        # get copy of cache
        result = self._cache_get_for_dn(dn)[1].copy()

        # remove special values that can't be added
        def delete_attribute(name):
            if name in result:
                del result[name]
        delete_attribute('entryUUID')
        delete_attribute('structuralObjectClass')
        delete_attribute('modifiersName')
        delete_attribute('subschemaSubentry')
        delete_attribute('entryDN')
        delete_attribute('modifyTimestamp')
        delete_attribute('entryCSN')
        delete_attribute('createTimestamp')
        delete_attribute('creatorsName')
        # turn into modlist list.
        modlist = tldap.modlist.addModlist(result)

        # on commit carry out action; on rollback restore cached state
        oncommit = lambda obj: obj.delete_s(dn)
        onrollback = lambda obj: obj.add_s(dn, modlist)
        return self._process(oncommit, onrollback, onfailure)

    def rename(self, dn, newrdn, new_base_dn=None, onfailure=None):
        """
        rename a dn in the ldap database; see ldap module. doesn't return a
        result if transactions enabled.
        """

        debug("\nrename", self, dn, newrdn, new_base_dn)

        # split up the parameters
        split_dn = ldap.dn.str2dn(dn)
        split_newrdn = ldap.dn.str2dn(newrdn)
        assert(len(split_newrdn) == 1)

        # make dn unqualified
        rdn = ldap.dn.dn2str(split_dn[0:1])

        # make newrdn fully qualified dn
        tmplist = []
        tmplist.append(split_newrdn[0])
        if new_base_dn is not None:
            tmplist.extend(ldap.dn.str2dn(new_base_dn))
            old_base_dn=ldap.dn.dn2str(split_dn[1:])
        else:
            tmplist.extend(split_dn[1:])
            old_base_dn=None
        newdn = ldap.dn.dn2str(tmplist)

        debug("--> cmmmit  ", self, dn, newrdn, new_base_dn)
        debug("--> rollback", self, newdn, rdn, old_base_dn)

        # on commit carry out action; on rollback reverse rename
        oncommit = lambda obj: obj.rename_s(dn, newrdn, new_base_dn)
        onrollback = lambda obj: obj.rename_s(newdn, rdn, old_base_dn)

        return self._process(oncommit, onrollback, onfailure)

    def fail(self):
        """ for testing purposes only. always fail in commit """

        debug("fail")

        # on commit carry out action; on rollback reverse rename
        oncommit = lambda obj: raise_testfailure("commit")
        onrollback = lambda obj: raise_testfailure("rollback")
        return self._process(oncommit, onrollback, None)

    # read only stuff

    def search(self, base, scope, filterstr='(objectClass=*)',
               attrlist=None, limit=None):
        """
        Search for entries in LDAP database.
        """

        debug("\nsearch", base, scope, filterstr, attrlist, limit)

        # first results
        if isinstance(attrlist, set):
            attrlist = list(attrlist)

        def first_results(obj):
            debug("---> searching ldap", limit)
            msgid = obj.search_ext(base, scope, filterstr, attrlist,
                                   sizelimit=limit or 0)
            return (msgid,) + self._obj.result3(msgid, 0)

        # get the 1st result
        try:
            msgid, result_type, result_list, result_msgid, result_serverctrls \
                = self._do_with_retry(first_results)
        except ldap.SIZELIMIT_EXCEEDED:
            debug("---> got SIZELIMIT_EXCEEDED")
            return

        # process the results
        while result_type and result_list:
            # Loop over list of search results
            for result_item in result_list:
                dn, attributes = result_item
                # did we already retrieve this from cache?
                debug("---> got ldap result", dn)
                debug("---> yielding", result_item)
                yield result_item
            try:
                result_type, result_list, result_msgid, result_serverctrls \
                    = self._obj.result3(msgid, 0)
            except ldap.SIZELIMIT_EXCEEDED:
                debug("---> got SIZELIMIT_EXCEEDED")
                return

        # we are finished - return results, eat cake
        return
