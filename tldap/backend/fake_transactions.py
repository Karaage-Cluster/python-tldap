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

""" This module provides the LDAP functions with transaction support faked,
with a subset of the functions from the real ldap module. """

import six
import tldap.dn
import ldap3
import tldap.exceptions
import tldap.modlist
import sys
import logging

from .base import LDAPbase

logger = logging.getLogger(__name__)


def _debug(*argv):
    argv = [str(arg) for arg in argv]
    logging.debug(" ".join(argv))


def raise_testfailure(place):
    raise tldap.exceptions.TestFailure("fail %s called" % place)


# errors

class NO_SUCH_OBJECT(Exception):
    pass


# wrapper class

class LDAPwrapper(LDAPbase):
    """ The LDAP connection class. """

    def __init__(self, settings_dict):
        super(LDAPwrapper, self).__init__(settings_dict)
        self._transact = False
        self._onrollback = []

    ####################
    # Cache Management #
    ####################

    def reset(self):
        """
        Reset transaction back to original state, discarding all
        uncompleted transactions.
        """
        super(LDAPwrapper, self).reset()
        self._onrollback = []

    def _cache_get_for_dn(self, dn):
        """
        Object state is cached. When an update is required the update will be
        simulated on this cache, so that rollback information can be correct.
        This function retrieves the cached data.
        """

        # no cached item, retrieve from ldap
        self._do_with_retry(
            lambda obj: obj.search(
                dn,
                '(objectclass=*)',
                ldap3.SEARCH_SCOPE_WHOLE_SUBTREE,
                attributes=['*', '+']))
        results = self._obj.response
        if len(results) < 1:
            raise NO_SUCH_OBJECT("No results finding current value")
        if len(results) > 1:
            raise RuntimeError("Too many results finding current value")

        return results[0]['raw_attributes']

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

        _debug("commit")
        self.reset()

    def rollback(self):
        """
        Roll back to previous database state. However stay inside transaction
        management.
        """
        if not self._transact:
            raise RuntimeError("rollback called outside transaction")

        _debug("rollback:", self._onrollback)
        # if something goes wrong here, nothing we can do about it, leave
        # database as is.
        try:
            # for every rollback action ...
            for onrollback, onfailure in self._onrollback:
                # execute it
                _debug("--> rolling back", onrollback)
                self._do_with_retry(onrollback)
                if onfailure is not None:
                    onfailure()

        except:
            _debug("--> rollback failed")
            exc_class, exc, tb = sys.exc_info()
            raise tldap.exceptions.RollbackError(
                "FATAL Unrecoverable rollback error: %r" % (exc))
        finally:
            # reset everything to clean state
            _debug("--> rollback success")
            self.reset()

    def _process(self, oncommit, onrollback, onfailure):
        """
        Process action. oncommit is a callback to execute action, onrollback is
        a callback to execute if the oncommit() has been called and a rollback
        is required
        """

        _debug("---> commiting", oncommit)
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

        _debug("add", self, dn, modlist)

        # if rollback of add required, delete it
        def oncommit(obj):
            obj.add(dn, None, modlist)

        def onrollback(obj):
            obj.delete(dn)

        # process this action
        return self._process(oncommit, onrollback, onfailure)

    def modify(self, dn, modlist, onfailure=None):
        """
        Modify a DN in the LDAP database; See ldap module. Doesn't return a
        result if transactions enabled.
        """

        _debug("modify", self, dn, modlist)

        # need to work out how to reverse changes in modlist; result in revlist
        revlist = {}

        # get the current cached attributes
        result = self._cache_get_for_dn(dn)

        # find the how to reverse modlist (for rollback) and put result in
        # revlist. Also simulate actions on cache.
        for mod_type, l in six.iteritems(modlist):
            mod_op, mod_vals = l

            reverse = None
            _debug("attribute:", mod_type)
            if mod_type in result:
                _debug("attribute cache:", result[mod_type])
            else:
                _debug("attribute cache is empty")
            _debug("attribute modify:", (mod_op, mod_vals))

            if mod_vals is not None:
                if not isinstance(mod_vals, list):
                    mod_vals = [mod_vals]

            if mod_op == ldap3.MODIFY_ADD:
                # reverse of MODIFY_ADD is MODIFY_DELETE
                reverse = (ldap3.MODIFY_DELETE, mod_vals)

            elif mod_op == ldap3.MODIFY_DELETE and len(mod_vals) > 0:
                # Reverse of MODIFY_DELETE is MODIFY_ADD, but only if value
                # is given if mod_vals is None, this means all values where
                # deleted.
                reverse = (ldap3.MODIFY_ADD, mod_vals)

            elif mod_op == ldap3.MODIFY_DELETE \
                    or mod_op == ldap3.MODIFY_REPLACE:
                if mod_type in result:
                    # If MODIFY_DELETE with no values or MODIFY_REPLACE
                    # then we have to replace all attributes with cached
                    # state
                    reverse = (
                        ldap3.MODIFY_REPLACE,
                        tldap.modlist.escape_list(result[mod_type])
                    )
                else:
                    # except if we have no cached state for this DN, in
                    # which case we delete it.
                    reverse = (ldap3.MODIFY_DELETE, None)

            else:
                raise RuntimeError("mod_op of %d not supported" % mod_op)

            _debug("attribute reverse:", reverse)
            if mod_type in result:
                _debug("attribute cache:", result[mod_type])
            else:
                _debug("attribute cache is empty")

            revlist[mod_type] = reverse

        _debug("--")
        _debug("modlist:", modlist)
        _debug("revlist:", revlist)
        _debug("--")

        # now the hard stuff is over, we get to the easy stuff
        def oncommit(obj):
            obj.modify(dn, modlist)

        def onrollback(obj):
            obj.modify(dn, revlist)

        return self._process(oncommit, onrollback, onfailure)

    def modify_no_rollback(self, dn, modlist):
        """
        Modify a DN in the LDAP database; See ldap module. Doesn't return a
        result if transactions enabled.
        """

        _debug("modify_no_rollback", self, dn, modlist)
        result = self._do_with_retry(lambda obj: obj.modify_s(dn, modlist))
        _debug("--")

        return result

    def delete(self, dn, onfailure=None):
        """
        delete a dn in the ldap database; see ldap module. doesn't return a
        result if transactions enabled.
        """

        _debug("delete", self)

        # get copy of cache
        result = self._cache_get_for_dn(dn)

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
        delete_attribute('hasSubordinates')
        delete_attribute('pwdFailureTime')
        delete_attribute('pwdChangedTime')
        # turn into modlist list.
        modlist = tldap.modlist.addModlist(result)

        _debug("revlist:", modlist)

        # on commit carry out action; on rollback restore cached state
        def oncommit(obj):
            obj.delete(dn)

        def onrollback(obj):
            obj.add(dn, None, modlist)

        return self._process(oncommit, onrollback, onfailure)

    def rename(self, dn, newrdn, new_base_dn=None, onfailure=None):
        """
        rename a dn in the ldap database; see ldap module. doesn't return a
        result if transactions enabled.
        """

        _debug("rename", self, dn, newrdn, new_base_dn)

        # split up the parameters
        split_dn = tldap.dn.str2dn(dn)
        split_newrdn = tldap.dn.str2dn(newrdn)
        assert(len(split_newrdn) == 1)

        # make dn unqualified
        rdn = tldap.dn.dn2str(split_dn[0:1])

        # make newrdn fully qualified dn
        tmplist = []
        tmplist.append(split_newrdn[0])
        if new_base_dn is not None:
            tmplist.extend(tldap.dn.str2dn(new_base_dn))
            old_base_dn = tldap.dn.dn2str(split_dn[1:])
        else:
            tmplist.extend(split_dn[1:])
            old_base_dn = None
        newdn = tldap.dn.dn2str(tmplist)

        _debug("--> commit  ", self, dn, newrdn, new_base_dn)
        _debug("--> rollback", self, newdn, rdn, old_base_dn)

        # on commit carry out action; on rollback reverse rename
        def oncommit(obj):
            obj.modify_dn(dn, newrdn, new_superior=new_base_dn)

        def onrollback(obj):
            obj.modify_dn(newdn, rdn, new_superior=old_base_dn)

        return self._process(oncommit, onrollback, onfailure)

    def fail(self):
        """ for testing purposes only. always fail in commit """

        _debug("fail")

        # on commit carry out action; on rollback reverse rename
        def oncommit(obj):
            raise_testfailure("commit")

        def onrollback(obj):
            raise_testfailure("rollback")

        return self._process(oncommit, onrollback, None)
