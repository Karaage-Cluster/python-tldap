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

""" This module provides the LDAP functions with transaction support disabled,
with a subset of the functions from the real ldap module. """

from .base import LDAPbase


# wrapper class

class LDAPwrapper(LDAPbase):
    """ The LDAP connection class. """

    ####################
    # Cache Management #
    ####################

    def reset(self, forceflushcache=False):
        """
        Reset transaction back to original state, discarding all
        uncompleted transactions.
        """
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
        """
        End a transaction. Must not be dirty when doing so. ie. commit() or
        rollback() must be called if changes made. If dirty, changes will be
        discarded.
        """
        pass

    def commit(self):
        """
        Attempt to commit all changes to LDAP database. i.e. forget all
        rollbacks.  However stay inside transaction management.
        """
        pass

    def rollback(self):
        """
        Roll back to previous database state. However stay inside transaction
        management.
        """
        pass

    ##################################
    # Functions needing Transactions #
    ##################################

    def add(self, dn, modlist, onfailure=None):
        """
        Add a DN to the LDAP database; See ldap module. Doesn't return a result
        if transactions enabled.
        """

        return self._do_with_retry(lambda obj: obj.add_s(dn, modlist))

    def modify(self, dn, modlist, onfailure=None):
        """
        Modify a DN in the LDAP database; See ldap module. Doesn't return a
        result if transactions enabled.
        """

        return self._do_with_retry(lambda obj: obj.modify_s(dn, modlist))

    def modify_no_rollback(self, dn, modlist):
        """
        Modify a DN in the LDAP database; See ldap module. Doesn't return a
        result if transactions enabled.
        """

        return self._do_with_retry(lambda obj: obj.modify_s(dn, modlist))

    def delete(self, dn, onfailure=None):
        """
        delete a dn in the ldap database; see ldap module. doesn't return a
        result if transactions enabled.
        """

        return self._do_with_retry(lambda obj: obj.delete_s(dn))

    def rename(self, dn, newrdn, newsuperior=None, onfailure=None):
        """
        rename a dn in the ldap database; see ldap module. doesn't return a
        result if transactions enabled.
        """

        return self._do_with_retry(
            lambda obj: obj.rename_s(dn, newrdn, newsuperior))
