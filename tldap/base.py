# Copyright 2012 VPAC
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

import tldap

import tldap.options
import tldap.exceptions
import tldap.manager

import ldap.dn
import ldap.modlist

import copy

class LDAPmeta(type):
    def __new__(cls, name, bases, attrs):
        super_new = super(LDAPmeta, cls).__new__
        parents = [b for b in bases if isinstance(b, LDAPmeta)]
        if not parents:
            # If this isn't a subclass of LDAPobject, don't do anything special.
            return super_new(cls, name, bases, attrs)

        module = attrs.pop('__module__')
        new_class = super_new(cls, name, bases, {'__module__': module})

        attr_meta = attrs.pop('Meta', None)

        new_class.add_to_class('_meta', tldap.options.Options(name, attr_meta))

        # Add all attributes to the class.
        ObjectDoesNotExist = tldap.exceptions.ObjectDoesNotExist
        new_class.add_to_class('DoesNotExist', subclass_exception(
                'tldap.exceptions.DoesNotExist',
                tuple(x.DoesNotExist for x in parents if hasattr(x, '_meta')) or (ObjectDoesNotExist,),
                module))
        MultipleObjectsReturned = tldap.exceptions.MultipleObjectsReturned
        new_class.add_to_class('MultipleObjectsReturned', subclass_exception(
                'MultipleObjectsReturned',
                tuple(x.MultipleObjectsReturned for x in parents if hasattr(x, '_meta')) or (MultipleObjectsReturned,),
                module))
        ObjectAlreadyExists = tldap.exceptions.ObjectAlreadyExists
        new_class.add_to_class('AlreadyExists', subclass_exception(
                'ObjectAlreadyExists',
                tuple(x.MultipleObjectsReturned for x in parents if hasattr(x, '_meta')) or (ObjectAlreadyExists,),
                module))

        for obj_name, obj in attrs.items():
            new_class.add_to_class(obj_name, obj)

        new_fields = new_class._meta.fields
        field_names = set([f.name for f in new_fields])
        parent_field_names = set()

        for i in ["_db_values", "dn", "_dn", "base_dn", "_base_dn" ]:
            if i in field_names:
                raise tldap.exceptions.FieldError('Local field %s clashes with reserved name from base class %r'%(i, name))

        for base in parents:
            if not hasattr(base, '_meta'):
                # Things without _meta aren't functional models, so they're
                # uninteresting parents.
                continue

            parent_fields = base._meta.fields
            for field in parent_fields:
                if field.name in field_names:
                    raise tldap.exceptions.FieldError('Local field %r in class %r clashes '
                                     'with field of similar name from base class %r' %
                                        (field.name, name, base.__name__))
                if field.name in parent_field_names:
                    raise tldap.exceptions.FieldError('Field %r from parent of class %r clashes '
                                     'with field of similar name from base class %r' %
                                        (field.name, name, base.__name__))
                new_class._meta.add_field(field)
                parent_field_names.add(field.name)

            new_class._meta.object_classes.update(base._meta.object_classes)


        new_class.add_to_class('objects', tldap.manager.LDAPmanager())
        return new_class

    def add_to_class(cls, name, value):
        if hasattr(value, 'contribute_to_class'):
            value.contribute_to_class(cls, name)
        else:
            setattr(cls, name, value)


def subclass_exception(name, parents, module):
    return type(name, parents, {'__module__': module})

class LDAPobject(object):
    __metaclass__ = LDAPmeta

    @property
    def dn(self):
        """Get the current dn."""
        return self._dn

    def __init__(self, **kwargs):
        self._db_values = {}
        self._alias = None
        self._dn = None
        self._base_dn = None

        fields = self._meta.fields
        field_names = set([f.name for f in fields])

        for k,v in kwargs.iteritems():
            if k in field_names:
                setattr(self, k, v)
            elif k == 'base_dn':
                setattr(self, '_base_dn', v)
            elif k == 'dn':
                setattr(self, '_dn', v)
            else:
                raise TypeError("'%s' is an invalid keyword argument for this function" % k)

        if self._dn is not None and self._base_dn is not None:
            raise ValueError("Makes no sense to set both dn and base_dn")

        if self._dn is None and self._base_dn is None:
            self._base_dn = self._meta.meta.base_dn

    def _reload_db_values(self, using=None):
        """
        Hack in case cached _db_values fall out of sync for any reason. Should not be needed anymore.
        """
        # what database should we be using?
        using = using or self._alias or tldap.DEFAULT_LDAP_ALIAS
        c = tldap.connections[using]

        # what fields should we get?
        fields = self._meta.fields
        field_names = [ f.name for f in fields ]

        # get values
        db_values = list(c.search(self._dn, ldap.SCOPE_BASE, attrlist=field_names))
        num = len(db_values)
        if num==0:
            raise self.DoesNotExist("%s matching query does not exist."
                    % self._meta.object_name)
        elif num > 1:
            raise self.model.MultipleObjectsReturned("get() returned more than one %s -- it returned %s!"
                    % (self._meta.object_name, num))

        self._db_values[using] = db_values[0][1]

    _reload_db_values.alters_data = True

    def construct_dn(self):
        raise RuntimeError("Need a full DN for this object")

    def rdn_to_dn(self, name):
        value = getattr(self, name)

        split_base = ldap.dn.str2dn(self._base_dn)
        split_newrdn = [[(name, value, 1)]] + split_base

        new_rdn = ldap.dn.dn2str(split_newrdn)

        return new_rdn

    def save(self, force_add=False, force_modify=False, using=None):
        """
        Saves the current instance. Override this in a subclass if you want to
        control the saving process.

        The 'force_insert' and 'force_update' parameters can be used to insist
        that the "save" must be an SQL insert or update (or equivalent for
        non-SQL backends), respectively. Normally, they should not be set.
        """
        if self._dn is None:
            self._dn = self.construct_dn()

        if force_add and force_modify:
            raise ValueError("Cannot force both insert and updating in model saving.")

        # what database should we be using?
        using = using or self._alias or tldap.DEFAULT_LDAP_ALIAS

        if force_add:
            self._add(using)
        elif force_modify:
            self._modify(using)
        elif using in self._db_values:
            self._modify(using)
        else:
            self._add(using)

    save.alters_data = True


    def delete(self, using=None):
        # what database should we be using?
        using = using or self._alias or tldap.DEFAULT_LDAP_ALIAS
        c = tldap.connections[using]

        # what to do if transaction is reversed
        old_values = self._db_values[using]
        def onfailure():
            self._db_values[using] = old_values

        # delete it
        c.delete(self._dn, onfailure)
        del self._db_values[using]

    delete.alters_data = True


    def _add(self, using):
        fields = self._meta.fields
        dn0k,dn0v,_ = ldap.dn.str2dn(self._dn)[0][0]

        # ensure objectClass is set
        self.objectClass = getattr(self, "objectClass", self._meta.object_classes)

        # generate moddict values
        moddict = {
            'objectClass': self.objectClass
        }
        for field in fields:
            name = field.name
            value = getattr(self, name, [])
            value = field.to_db(value)
            # if dn attribute given, it must match the dn
            if name == dn0k:
                if len(value) < 1:
                    value = [ dn0v]
                if dn0v.lower() not in set(v.lower() for v in value):
                    raise ValueError("value of %r is %r does not include %r from dn %r"%(name, value, dn0v, self._dn))
            moddict[name] = value

        # turn moddict into a modlist
        modlist = ldap.modlist.addModlist(moddict)

        # what database should we be using?
        c = tldap.connections[using]

        # what to do if transaction is reversed
        def onfailure():
            del self._db_values[using]

        # do it
        try:
            c.add(self._dn, modlist, onfailure)
        except ldap.ALREADY_EXISTS:
            raise self.AlreadyExists("Object with dn %r already exists doing add"%(self._dn,))

        # update dn attribute in object
        field_names = set([f.name for f in fields])
        if dn0k in field_names:
            setattr(self, dn0k, dn0v)

        # save new values
        self._db_values[using] = moddict

    _add.alters_data = True


    def _modify(self, using):
        assert(using in self._db_values)
        fields = self._meta.fields
        dn0k,dn0v,_ = ldap.dn.str2dn(self._dn)[0][0]

        # what database should we be using?
        c = tldap.connections[using]

        # generate moddict values
        moddict = {}
        for field in fields:
            name = field.name
            value = getattr(self, name, [])
            value = field.to_db(value)
            # if dn attribute given, it must match the dn
            if name == dn0k:
                if len(value) < 1:
                    value = [ dn0v ]
                if dn0v.lower() not in set(v.lower() for v in value):
                    raise ValueError("value of %r is %r does not include %r from dn %r"%(name, value, dn0v, self._dn))
            moddict[name] = value

        # turn moddict into a modlist
        modlist = ldap.modlist.modifyModlist(self._db_values[using], moddict)

        # what to do if transaction is reversed
        old_values = self._db_values[using]
        def onfailure():
            self._db_values[using] = old_values

        # do it
        try:
            c.modify(self._dn, modlist, onfailure)
        except ldap.NO_SUCH_OBJECT:
            raise self.DoesNotExist("Object with dn %r doesn't already exist doing modify"%(self._dn,))

        # save new values
        self._db_values[using] = moddict

    _modify.alters_data = True

    def rename(self, name, value, using=None):
        # what database should we be using?
        using = using or self._alias or tldap.DEFAULT_LDAP_ALIAS
        c = tldap.connections[using]

        # what to do if transaction is reversed
        old_dn = self._dn
        old_values = copy.copy(self._db_values[using])
        def onfailure():
            self._dn = old_dn
            self._db_values[using] = old_values

        # do the rename
        split_newrdn = [[(name, value, 1)]]
        new_rdn = ldap.dn.dn2str(split_newrdn)
        c.rename(self._dn, new_rdn, onfailure)

        # reconstruct dn
        split_dn = ldap.dn.str2dn(self._dn)

        # make newrdn fully qualified dn
        tmplist = []
        tmplist.append(split_newrdn[0])
        tmplist.extend(split_dn[1:])
        self._dn = ldap.dn.dn2str(tmplist).lower()

        # get set of field_names
        fields = self._meta.fields

        # get old rdn values
        split_oldrdn = ldap.dn.str2dn(self._dn)
        old_key,old_value,_ = split_dn[0][0]

        for field in fields:
            # delete old rdn attribute in object
            if field.name == old_key:
                v = getattr(self, old_key, [])
                if v is None:
                    pass
                elif isinstance(v, list):
                    if old_value in v:
                        v.remove(old_value)
                    if len(v)==0:
                        v = None
                elif old_value == v:
                    v = None
                v = field.to_db(v)
                if v == None:
                    del self._db_values[using][old_key]
                else:
                    self._db_values[using][old_key] = v
                v = field.clean(v)
                setattr(self, old_key, v)

            # update new rdn attribute in object
            if field.name == name:
                v = getattr(self, name, None)
                if v is None:
                    v = value
                elif isinstance(v, list):
                    if value not in v:
                        v.append(value)
                elif v != value:
                    v = [ v, value ]
                v = field.to_db(v)
                self._db_values[using][name] = v
                v = field.clean(v)
                setattr(self, name, v)

    rename.alters_data = True
