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

""" This module provides the LDAP functions with transaction support faked,
with a subset of the functions from the real ldap module.  Note that the async
and sync functions are identical. When transactions are not enabled they will
behave like the sync functions and return the same information.

When transactions are enabled, the action will be delayed until commit() is
called. This means that rollback() is normally a nop. This could also be easily
changed to make the changes immediately and rollback if required.

The current state is simulated in cache, so that functions to retrieve
the current data should work as expected.

WARNING: DON'T use more then one object/connection per database; if you have
multiple LDAPObject values for the one database things could get confused
because each one will keep track of changes seperately - if this is an issue
the caching functionality could be split into a seperate class."""

import ldap
import ldap.modlist
import ldap.dn
import ldaptor
import ldaptor.entryhelpers
import tldap.exceptions
import copy
import sys

# hardcoded settings for this module

debugging = False
delayed_connect = True

# debugging

def debug(*argv):
    argv = [ str(arg) for arg in argv ]
    if debugging:
        print " ".join(argv)

def raise_testfailure(place):
    raise tldap.exceptions.TestFailure("fail %s called"%place)

# private

class Filter(ldaptor.entryhelpers.MatchMixin):
    def __init__(self, dn, attributes):
        self._dn = dn
        self._attributes = attributes

    def get(self, key, default):
        return self._attributes.get(key, default)

    def __getitem__(self, key):
        return self._attributes.get(key)

    def __contains__(self, item):
        return item in self._attributes

# wrapper class

class LDAPwrapper(object):

    def __init__(self, settings_dict):
        self.settings_dict = settings_dict
        self._transact = False
        self._obj = None
        self.search_in_progress = False

        self._cache = None
        self._oncommit = None
        self._onrollback = None
        self._bind_args = None
        self._bind_kwargs = None

        # just autoflushes the cache after every transaction
        # not strictly required, however guarantees that one transaction
        # can't stuff up future transactions if something went wrong
        # with the caching
        self.autoflushcache = True
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
        self._oncommit = []
        self._onrollback = []
        if forceflushcache or self.autoflushcache:
            self._cache = {}

    def _cache_normalize_dn(self, dn):
        """ normalize the dn, i.e. remove unwanted white space - hopefully this will mean it
        is not possible to have two or more cache entries representing the same ldap entry. """
        return ldap.dn.dn2str(ldap.dn.str2dn(dn))

    def _cache_get_for_dn(self, dn):
        """ Object state is cached. When an update is required the update will be simulated on this cache,
        so that rollback information can be correct. This function retrieves the cached data. """
        dn = self._cache_normalize_dn(dn).lower()
        if dn not in self._cache:
            # no cached item, retrieve from ldap
            results = self._do_with_retry(lambda obj: obj.search_s(dn, ldap.SCOPE_BASE, '(objectclass=*)', ['*','+']))
            if len(results) < 1:
                raise ldap.NO_SUCH_OBJECT("No results finding current value")
            if len(results) > 1:
                raise RuntimeError("Too many results finding current value")
            self._cache[dn] = results[0]

        elif self._cache[dn] is None:
            # don't allow access to deleted items
            raise ldap.NO_SUCH_OBJECT("Object with dn %s was deleted in cache"%dn)

        # return result
        return self._cache[dn]

    def _cache_create_for_dn(self, dn):
        """ Object state is cached. When an update is required the update will be simulated on this cache,
        so that rollback information can be correct. This function retrieves the cached data. """
        dn = self._cache_normalize_dn(dn)
        ldn = dn.lower()
        if ldn in self._cache and self._cache[ldn] is not None:
            raise ldap.ALREADY_EXISTS("Object with dn %s already exists in cache"%dn)
        self._cache[ldn] = ( dn, {} )
        return self._cache[ldn]

    def _cache_rename_dn(self, dn, newdn):
        """ The function will rename the DN in the cache. """
        newdn = self._cache_normalize_dn(newdn)
        lnewdn = newdn.lower()
        if newdn in self._cache and self._cache[lnewdn] is not None:
            raise ldap.ALREADY_EXISTS("Object with dn %s already exists in cache"%newdn)

        cache = self._cache_get_for_dn(dn)
        self._cache_del_dn(dn)

        self._cache[lnewdn] = (newdn, cache[1])

    def _cache_del_dn(self, dn):
        """ This function will mark as deleted the DN created with _cache_get_for_dn and mark it as unsuable. """
        dn = self._cache_normalize_dn(dn).lower()
        if dn in self._cache:
            self._cache[dn] = None

    ##########################
    # Transaction Management #
    ##########################

    def is_dirty(self):
        """ Are there uncommitted changes? """
        if len(self._oncommit) > 0:
            return True
        if len(self._onrollback) > 0:
            return True
        return False

    def is_managed(self):
        """ Are we inside transaction management? """
        return self._transact

    def enter_transaction_management(self):
        """ Start a transaction. """
        if self._transact:
            raise RuntimeError("enter_transaction_management called inside transaction")

        self._transact = True
        self._oncommit = []
        self._onrollback = []

    def leave_transaction_management(self):
        """ End a transaction. Must not be dirty when doing so. ie. commit() or
        rollback() must be called if changes made. If dirty, changes will be discarded. """
        if not self._transact:
            raise RuntimeError("leave_transaction_management called outside transaction")
        if len(self._oncommit) > 0:
            self.reset(forceflushcache=True)
            raise RuntimeError("leave_transaction_management called with uncommited changes")
        if len(self._onrollback) > 0:
            self.reset(forceflushcache=True)
            raise RuntimeError("leave_transaction_management called with uncommited rollbacks")
        self.reset()
        self._transact = False

    def commit(self):
        """ Attempt to commit all changes to LDAP database, NOW! However stay inside transaction management. """
        if not self._transact:
            raise RuntimeError("commit called outside transaction")

        debug("\ncommit", self._oncommit)
        try:
            # for every action ...
            for oncommit, onrollback, _ in self._oncommit:
                # execute it
                debug("---> commiting", oncommit)
                self._do_with_retry(oncommit)
                # add statement to rollback log in case something goes wrong
                self._onrollback.insert(0, onrollback)
        except:
            # oops. Something went wrong. Attempt to rollback.
            debug("commit failed")
            self.rollback()
            # rollback appears to have worked, reraise exception
            raise
        finally:
            # reset everything to clean state
            self.reset()

    def rollback(self):
        """ Roll back to previous database state. However stay inside transaction management. """
        if not self._transact:
            raise RuntimeError("rollback called outside transaction")

        debug("\nrollback:", self._onrollback)
        # if something goes wrong here, nothing we can do about it, leave
        # database as is.
        try:
            # for every rollback action ...
            for onrollback in self._onrollback:
                # execute it
                debug("rolling back", onrollback)
                self._do_with_retry(onrollback)

            for _, _, onfailure in reversed(self._oncommit):
                if onfailure is not None:
                    debug("failure", onfailure)
                    onfailure()

        except:
            debug("rollback failed")
            exc_class, exc, tb = sys.exc_info()
            new_exc = tldap.exceptions.RollbackError("FATAL Unrecoverable rollback error: %r"%(exc))
            raise new_exc.__class__, new_exc, tb
        finally:
            # reset everything to clean state
            self.reset(forceflushcache=True)

    def _process(self, oncommit, onrollback, onfailure):
        """ Add action to list. oncommit is a callback to execute on commit(),
        onrollback is a callback to execute if the oncommit() has been called and
        a rollback is required """
        if not self._transact:
            result = self._do_with_retry(oncommit)
            self.reset()
            return result
        else:
            self._oncommit.append( (oncommit, onrollback, onfailure) )
            return None

    ##################################
    # Functions needing Transactions #
    ##################################

    def add(self, dn, modlist, onfailure=None):
        """ Add a DN to the LDAP database; See ldap module. Doesn't return a
        result if transactions enabled. """

        debug("\nadd", self, dn, modlist)
        assert not self.search_in_progress

        # if rollback of add required, delete it
        oncommit   = lambda obj: obj.add_s(dn, modlist)
        onrollback = lambda obj: obj.delete_s(dn)

        # simulate this action in cache
        cache = self._cache_create_for_dn(dn)
        k,v,_ = ldap.dn.str2dn(dn)[0][0]
        cache[1][k] = [v]
        for k,v in modlist:
            if isinstance(v, list):
                cache[1][k] = v
            else:
                cache[1][k] = [v]

        # process this action
        return self._process(oncommit, onrollback, onfailure)


    def modify(self, dn, modlist, onfailure=None):
        """ Modify a DN in the LDAP database; See ldap module. Doesn't return a
        result if transactions enabled. """

        debug("\nmodify", self, dn, modlist)
        assert not self.search_in_progress

        # need to work out how to reverse changes in modlist; result in revlist
        revlist = []

        # get the current cached attributes
        result = self._cache_get_for_dn(dn)[1]

        # find the how to reverse modlist (for rollback) and put result in
        # revlist. Also simulate actions on cache.
        for mod_op,mod_type,mod_vals in modlist:
            reverse = None
            if mod_type in result:
                debug("attribute cache:", result[mod_type])
            else:
                debug("attribute cache is empty")
            debug("attribute modify:", (mod_op, mod_type, mod_vals))

            if mod_vals is not None:
                if not isinstance(mod_vals, list):
                    mod_vals = [ mod_vals ]

            if mod_op == ldap.MOD_ADD:
                # reverse of MOD_ADD is MOD_DELETE
                reverse = (ldap.MOD_DELETE,mod_type,mod_vals)

                # also carry out simulation in cache
                if mod_type not in result:
                    result[mod_type] = []

                for val in mod_vals:
                    if val in result[mod_type]:
                        raise ldap.TYPE_OR_VALUE_EXISTS("%s value %s already exists"%(mod_type,val))
                    result[mod_type].append(val)

            elif mod_op == ldap.MOD_DELETE and mod_vals is not None:
                # Reverse of MOD_DELETE is MOD_ADD, but only if value is given
                # if mod_vals is None, this means all values where deleted.
                reverse = (ldap.MOD_ADD,mod_type,mod_vals)

                # also carry out simulation in cache
                if mod_type not in result:
                    raise ldap.NO_SUCH_ATTRIBUTE("%s value doesn't exist"%mod_type)

                for val in mod_vals:
                    if val not in result[mod_type]:
                        raise ldap.NO_SUCH_ATTRIBUTE("%s value %s doesn't exist"%(mod_type,val))
                    result[mod_type].remove(val)

                if len(result[mod_type]) == 0:
                    del result[mod_type]

            elif mod_op == ldap.MOD_DELETE or mod_op == ldap.MOD_REPLACE:
                if mod_type in result:
                    # If MOD_DELETE with no values or MOD_REPLACE then we
                    # have to replace all attributes with cached state
                    reverse = (ldap.MOD_REPLACE,mod_type,result[mod_type])
                else:
                    # except if we have no cached state for this DN, in which case we delete it.
                    reverse = (ldap.MOD_DELETE,mod_type,None)

                # also carry out simulation in cache
                if mod_vals is not None:
                    result[mod_type] = mod_vals
                elif mod_type in result:
                    del result[mod_type]

            else:
                raise RuntimeError("mod_op of %d not supported"%mod_op)

            debug("attribute reverse:", reverse)
            if mod_type in result:
                debug("attribute cache:", result[mod_type])
            else:
                debug("attribute cache is empty")

            revlist.insert(0, reverse)

        debug("--\n")

        # now the hard stuff is over, we get to the easy stuff
        oncommit   = lambda obj: obj.modify_s(dn, modlist)
        onrollback = lambda obj: obj.modify_s(dn, revlist)
        return self._process(oncommit, onrollback, onfailure)

    def delete(self, dn, onfailure=None):
        """ delete a dn in the ldap database; see ldap module. doesn't return a
        result if transactions enabled. """

        debug("\ndelete", self)
        assert not self.search_in_progress

        # get copy of cache
        result = self._cache_get_for_dn(dn)[1].copy()

        # remove special values that can't be added
        def delete_attribute(name):
            if name in result: del result[name]
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
        modlist = ldap.modlist.addModlist(result)
        # delete the cache entry
        self._cache_del_dn(dn)

        # on commit carry out action; on rollback restore cached state
        oncommit   = lambda obj: obj.delete_s(dn)
        onrollback = lambda obj: obj.add_s(dn, modlist)
        return self._process(oncommit, onrollback, onfailure)

    def rename(self, dn, newrdn, onfailure=None):
        """ rename a dn in the ldap database; see ldap module. doesn't return a
        result if transactions enabled. """

        debug("\nrename", self, dn, newrdn)
        assert not self.search_in_progress

        # split up the parameters
        split_dn = ldap.dn.str2dn(dn)
        split_newrdn = ldap.dn.str2dn(newrdn)
        assert(len(split_newrdn)==1)

        # make dn unqualified
        rdn = ldap.dn.dn2str(split_dn[0:1])

        # make newrdn fully qualified dn
        tmplist = []
        tmplist.append(split_newrdn[0])
        tmplist.extend(split_dn[1:])
        newdn = ldap.dn.dn2str(tmplist)

        debug("--> rollback", self, newdn, rdn)

        # on commit carry out action; on rollback reverse rename
        oncommit   = lambda obj: obj.rename_s(dn, newrdn)
        onrollback = lambda obj: obj.rename_s(newdn, rdn)

        debug("--> rename cache", dn, newdn)
        self._cache_rename_dn(dn, newdn)
        cache = self._cache_get_for_dn(newdn)[1]
        old_key,old_value,_ = split_dn[0][0]
        if old_value in cache[old_key]:
            cache[old_key].remove(old_value)
        if len(cache[old_key]) == 0:
            del cache[old_key]
        new_key,new_value,_ = split_newrdn[0][0]
        if new_key not in cache:
            cache[new_key] = [ ]
        if new_value not in cache[new_key]:
            cache[new_key].append(new_value)

        return self._process(oncommit, onrollback, onfailure)

    def fail(self):
        """ for testing purposes only. always fail in commit """

        debug("fail")

        # on commit carry out action; on rollback reverse rename
        oncommit   = lambda obj: raise_testfailure("commit")
        onrollback = lambda obj: raise_testfailure("rollback")
        return self._process(oncommit, onrollback, None)

    # read only stuff

    def search(*args, **kwargs):
        """ Search for entries in LDAP database. """
        assert not self.search_in_progress

        # nested searches are not allowed
        self.search_in_progress = True
        try:
            self._search(*args, **kwargs)
        except:
            self.search_in_progress = False
            raise
        self.search_in_progress = False
        return

    def search(self, base, scope, filterstr='(objectClass=*)', attrlist=None, limit=None):
        """ Search for entries in LDAP database. """

        debug("\nsearch", base, scope, filterstr, attrlist, limit)

        # parse the filter string
        debug("---> filterstr", filterstr)
        if filterstr is not None:
            if filterstr[0] != "(":
                filterstr = "(%s)"%filterstr

            filterobj = ldaptor.ldapfilter.parseFilter(filterstr)
        else:
            filterobj = None
        debug("---> filterobj", type(filterobj))

        # is this dn in the search scope?
        split_base = ldap.dn.str2dn(base.lower())
        base = ldap.dn.dn2str(split_base)
        def check_scope(dn):
            split_dn = ldap.dn.str2dn(dn)

            if dn == base:
                return True

            nested = len(split_dn) - len(split_base)
            if scope == ldap.SCOPE_BASE:
                pass
            elif scope == ldap.SCOPE_ONELEVEL:
                if nested == 1:
                    for i in range(len(split_base)):
                        if split_dn[i+nested] != split_base[i]:
                            return False
                    return True
            elif scope == ldap.SCOPE_SUBTREE:
                if nested > 0:
                    for i in range(len(split_base)):
                        if split_dn[i+nested] != split_base[i]:
                            return False
                    return True
            else:
                raise RuntimeError("Unknown search scope %d"%scope)

            return False

        # search cache
        rset = set()
        for dn, v in self._cache.iteritems():
            if limit is not None and limit == 0:
                return

            debug("---> checking", dn, v)

            # check dn is in search scope
            if not check_scope(dn):
                debug("---> not in scope")
                continue
            debug("---> is in scope")

            # if this entry is not deleted
            if v is not None:
                item_dn, item_attributes = v
                # then check if it matches the filter
                t = Filter(item_dn, item_attributes)
                if filterobj is None or t.match(filterobj):
                    debug("---> match")
                    rset.add(dn)
                    debug("---> yielding", v)
                    yield copy.deepcopy(v)
                    if limit is not None:
                        limit = limit - 1
                else:
                    debug("---> nomatch")
            else:
                # otherwise, entry deleted in cache, delete from
                # results
                debug("---> deleted")
                rset.add(dn)


        # first results
        if isinstance(attrlist, set):
            attrlist = list(attrlist)
        def first_results(obj):
            msgid = obj.search_ext(base, scope, filterstr, attrlist, sizelimit=limit or 0)
            return (msgid,) + self._obj.result3(msgid, 0)

        # get the 1st result
        try:
            msgid,result_type,result_list,result_msgid,result_serverctrls = self._do_with_retry(first_results)
        except ldap.NO_SUCH_OBJECT:
            # if base doesn't exist in LDAP, it really should exist in cache
            debug("---> got NO_SUCH_OBJECT")
            self._cache_get_for_dn(base)
            debug("---> ... but ok because base is cached")
            return

        # process the results
        while result_type and result_list:
            # Loop over list of search results
            for result_item in result_list:
                dn, attributes = result_item
                # did we already retrieve this from cache?
                debug("---> got ldap result", dn)
                if dn.lower() not in rset:
                    debug("---> yielding", result_item)
                    yield result_item
            result_type,result_list,result_msgid,result_serverctrls = self._obj.result3(msgid, 0)

        # we are finished - return results, eat cake
        return
