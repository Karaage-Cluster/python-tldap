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
        new_class.add_to_class('objects', tldap.manager.Manager())

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
        field_names = new_class._meta.get_all_field_names()
        parent_field_names = dict()

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
                    if type(field) != type(parent_field_names[field.name]):
                        raise tldap.exceptions.FieldError('In class %r field %r from parent clashes '
                                     'with field of similar name from base class %r and is different type' %
                                        (name, field.name, base.__name__))
                parent_field_names[field.name] = field
                new_class._meta.add_field(field)

            new_class._meta.object_classes.update(base._meta.object_classes)
            base_dn = getattr(new_class._meta, 'base_dn', None) or getattr(base._meta, 'base_dn', None)
            new_class._meta.base_dn = base_dn

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

    def get_fields(self):
        for i in self._meta.get_all_field_names():
            yield i, getattr(self, i)

    def __init__(self, **kwargs):
        self._db_values = {}
        self._alias = None
        self._dn = None
        self._base_dn = None

        fields = self._meta.fields

        for field in fields:
            if field.name in kwargs:
                value = kwargs.pop(field.name)
            else:
                value = field.to_python([])

            setattr(self, field.name, value)


        if 'base_dn' in kwargs:
            value = kwargs.pop('base_dn')
            setattr(self, '_base_dn', value)

        if 'dn' in kwargs:
            value = kwargs.pop('dn')
            setattr(self, '_dn', value)

        for key in kwargs:
            raise TypeError("'%s' is an invalid keyword argument for this function" % key)

        if self._dn is not None and self._base_dn is not None:
            raise ValueError("Makes no sense to set both dn and base_dn")

        if self._dn is None and self._base_dn is None:
            self._base_dn = self._meta.base_dn

    def load_db_values(self, using=None):
        """
        Kludge to load DB values from other databases. Required for multiple DB use.
        """
        # what database should we be using?
        using = using or self._alias or tldap.DEFAULT_LDAP_ALIAS
        c = tldap.connections[using]

        if using in self._db_values:
            return

        # what fields should we get?
        field_names = self._meta.get_all_field_names()

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

    load_db_values.alters_data = True

    def construct_dn(self):
        raise RuntimeError("Need a full DN for this object")

    def rdn_to_dn(self, name):
        field = self._meta.get_field_by_name(name)
        value = getattr(self, name)
        value = field.value_to_db(value)

        split_base = ldap.dn.str2dn(self._base_dn)
        split_new_rdn = [[(name, value, 1)]] + split_base

        new_rdn = ldap.dn.dn2str(split_new_rdn)

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


    def _get_moddict(self, default_object_class, default_object_class_db, using):
        dn0k,dn0v,_ = ldap.dn.str2dn(self._dn)[0][0]

        # get field for objectClass or a default if there is none.
        try:
            object_class_field = self._meta.get_field_by_name("objectClass")
        except KeyError:
            object_class_field = tldap.fields.CharField(max_instances = None)

        # convert python value to db value or vice versa as required.
        if default_object_class is None:
            default_object_class = object_class_field.clean(default_object_class_db)
        elif default_object_class_db is None:
            default_object_class_db = object_class_field.to_db(default_object_class)
        else:
            assert False

        # even if objectClass isn't a field in the model, we still need to set it
        moddict = {
            'objectClass': default_object_class_db
        }

        # generate moddict values
        fields = self._meta.fields
        for field in fields:
            name = field.name
            value = getattr(self, name)
            # if dn attribute not given, try to set it, otherwise just convert value
            if name == dn0k:
                if isinstance(value, list) and len(value) == 0:
                    value = [ dn0v ]
                    setattr(self, name, field.clean(value))
                elif value is None:
                    value = [ dn0v ]
                    setattr(self, name, field.clean(value))
                else:
                    value = field.to_db(value)
            # if objectClass not given, try to set it, otherwise just convert value
            elif name == 'objectClass':
                assert isinstance(value, list)
                if len(value) == 0:
                    value = default_object_class_db
                    setattr(self, name, default_object_class)
                else:
                    value = field.to_db(value)
            # otherwise just convert value
            else:
                value = field.to_db(value)
            # db value should always be a list
            assert isinstance(value, list)
            # if dn attribute given, it must match the dn
            if name == dn0k:
                if dn0v.lower() not in set(v.lower() for v in value):
                    raise ValueError("value of %r is %r does not include %r from dn %r"%(name, value, dn0v, self._dn))
            moddict[name] = value
        return moddict

    def _add(self, using):
        # default object class if none given
        default_object_class = getattr(self, "objectClass", [])
        default_object_class_db = None
        if len(default_object_class) == 0:
            default_object_class = None
            default_object_class_db = list(self._meta.object_classes)

        # generate moddict values
        moddict = self._get_moddict(default_object_class, default_object_class_db, using)

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

        # save new values
        self._db_values[using] = moddict

    _add.alters_data = True


    def _modify(self, using):
        assert(using in self._db_values)
        fields = self._meta.fields

        # what database should we be using?
        c = tldap.connections[using]

        # default object class if none given
        default_object_class_db = self._db_values[using]['objectClass']

        # even if objectClass isn't a field, we still need to set it
        modold = {
            'objectClass': default_object_class_db
        }

        # generate modold values
        fields = self._meta.fields
        for field in fields:
            name = field.name
            modold[name] = self._db_values[using].get(name, [])

        # generate moddict values
        moddict = self._get_moddict(None, default_object_class_db, using)

        # turn moddict into a modlist
        modlist = ldap.modlist.modifyModlist(modold, moddict)

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

    def rename(self, **kwargs):
        assert len(kwargs)==1
        name,value = kwargs.iteritems().next()

        if isinstance(value, unicode):
            value = value.encode()

        split_new_rdn = [[(name, value, 1)]]
        new_rdn = ldap.dn.dn2str(split_new_rdn)

        # what database should we be using?
        for using in list(self._db_values):
            self._rename(new_rdn, using)

        # construct new dn
        split_dn = ldap.dn.str2dn(self._dn)
        tmplist = []
        tmplist.append(split_new_rdn[0])
        tmplist.extend(split_dn[1:])
        self._dn = ldap.dn.dn2str(tmplist)

    rename.alters_data = True

    def _rename(self, new_rdn, using):
        c = tldap.connections[using]

        # what to do if transaction is reversed
        old_dn = self._dn
        old_values = self._db_values[using]
        def onfailure():
            self._dn = old_dn
            self._db_values[using] = old_values

        # do the rename
        c.rename(self._dn, new_rdn, onfailure)

        # get old rdn values
        split_old_dn = ldap.dn.str2dn(self._dn)
        old_key,old_value,_ = split_old_dn[0][0]

        # get new rdn values
        split_new_rdn = ldap.dn.str2dn(new_rdn)
        new_key,new_value,_ = split_new_rdn[0][0]

        # make a copy before modifications
        self._db_values[using] = copy.copy(self._db_values[using])

        # delete old rdn attribute in object
        field = self._meta.get_field_by_name(old_key)
        v = getattr(self, old_key, [])
        old_value = field.value_to_python(old_value)
        if v is None:
            pass
        elif isinstance(v, list):
            v = [ x for x in v if x.lower() != old_value.lower()]
        elif old_value.lower() == v.lower():
            v = None
        if v == None:
            del self._db_values[using][old_key]
        else:
            self._db_values[using][old_key] = field.to_db(v)
        setattr(self, old_key, v)

        # update new rdn attribute in object
        field = self._meta.get_field_by_name(new_key)
        v = getattr(self, new_key, None)
        new_value = field.value_to_python(new_value)
        if v is None:
            v = new_value
        elif isinstance(v, list):
            if new_value.lower() not in [ x.lower() for x in v ]:
                v.append(new_value)
        elif v.lower() != new_value.lower():
            # we can't add a value to a string
            assert False
        self._db_values[using][new_key] = field.to_db(v)
        setattr(self, new_key, v)

    _rename.alters_data = True
