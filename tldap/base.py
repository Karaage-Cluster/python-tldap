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

import tldap
import tldap.options
import tldap.exceptions
import tldap.manager
import tldap.fields

import ldap.dn
import ldap.modlist

import copy
import sys

default_object_class_field = tldap.fields.CharField(required=True, max_instances=None)

class LDAPmeta(type):
    def __new__(cls, name, bases, attrs):
        super_new = super(LDAPmeta, cls).__new__
        parents = [b for b in bases if isinstance(b, LDAPmeta)]
        if not parents:
            # If this isn't a subclass of LDAPobject, don't do anything special.
            return super_new(cls, name, bases, attrs)

        # create new class
        module = attrs.pop('__module__')
        new_class = super_new(cls, name, bases, {'__module__': module})

        # get the attributes to add
        attr_meta = attrs.pop('Meta', None)
        meta = attr_meta
        base_meta = getattr(new_class, '_meta', None)

        # get the app_label for this model
        if getattr(meta, 'app_label', None) is None:
            # Figure out the app_label by looking one level up.
            # For 'django.contrib.sites.models', this would be 'sites'.
            model_module = sys.modules[new_class.__module__]
            kwargs = {"app_label": model_module.__name__.split('.')[-2]}
        else:
            kwargs = {}

        # add the _meta and objectClass to new class
        new_class.add_to_class('_meta', tldap.options.Options(meta, **kwargs))
        new_class.add_to_class('objectClass', default_object_class_field)

        # inherit certain attributes from parent
        if base_meta is not None:
            if new_class._meta.base_dn is None:
                new_class._meta.base_dn = base_meta.base_dn
            if new_class._meta.pk is None:
                new_class._meta.pk = base_meta.pk

        # create the default manager
        manager = tldap.manager.Manager()
        new_class.add_to_class('objects', manager)
        new_class.add_to_class('_default_manager', manager)

        # add exceptions to the class
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

        # add rest of attributes to class
        for obj_name, obj in attrs.items():
            new_class.add_to_class(obj_name, obj)

        # list of field names
        new_fields = new_class._meta.fields
        field_names = new_class._meta.get_all_field_names()

        # check for clashes with reserved names
        for i in ["_db_values", "dn", "_dn", "base_dn", "_base_dn" ]:
            if i in field_names:
                raise tldap.exceptions.FieldError('Local field %s clashes with reserved name from base class %r'%(i, name))

        # for every parent ...
        parent_field_names = dict()
        for base in parents:
            if not hasattr(base, '_meta'):
                # Things without _meta aren't functional models, so they're
                # uninteresting parents.
                continue

            # for every field in every parent ...
            parent_fields = base._meta.fields
            for field in parent_fields:
                # check if this field from this parent clashes
                if field.name == "objectClass":
                    # objectClass will always clash with parent classes, as we added it
                    # allow it as an exception
                    continue
                if field.name in field_names:
                    raise tldap.exceptions.FieldError('Local field %r in class %r clashes '
                                     'with field of similar name from base class %r' %
                                        (field.name, name, base.__name__))
                if field.name in parent_field_names:
                    if type(field) != type(parent_field_names[field.name]):
                        raise tldap.exceptions.FieldError('In class %r field %r from parent clashes '
                                     'with field of similar name from base class %r and is different type' %
                                        (name, field.name, base.__name__))
                else:
                    parent_field_names[field.name] = field
                    new_class._meta.add_field(field)

            # these meta values are all parents combined
            new_class._meta.object_classes.update(base._meta.object_classes)
            new_class._meta.search_classes.update(base._meta.search_classes)

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

    @property
    def pk(self):
        return getattr(self, self._meta.pk)

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        if self.pk != other.pk:
            return False
        return True

    def __ne__(self, other):
        return not (self == other)

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

    def rdn_to_dn(self, name):
        field = self._meta.get_field_by_name(name)
        value = getattr(self, name)
        if value is None:
            raise tldap.exceptions.ValidationError("Cannot use %s in dn as it is None"%name)
        if isinstance(value, list):
            raise tldap.exceptions.ValidationError("Cannot use %s in dn as it is a list"%name)
        value = field.value_to_db(value)

        split_base = ldap.dn.str2dn(self._base_dn)
        split_new_dn = [[(name, value, 1)]] + split_base

        new_dn = ldap.dn.dn2str(split_new_dn)

        return new_dn

    def save(self, force_add=False, force_modify=False, using=None):
        """
        Saves the current instance. Override this in a subclass if you want to
        control the saving process.

        The 'force_insert' and 'force_update' parameters can be used to insist
        that the "save" must be an SQL insert or update (or equivalent for
        non-SQL backends), respectively. Normally, they should not be set.
        """
        if self._dn is None and self._meta.pk is not None:
            self._dn = self.rdn_to_dn(self._meta.pk)

        if self._dn is None:
            raise tldap.exceptions.ValidationError("Need a full DN for this object")

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

        # get field for objectClass
        object_class_field = self._meta.get_field_by_name("objectClass")

        # convert python value to db value or vice versa as required.
        tmp_default_object_class = set()
        tmp_default_object_class_db = set()

        if len(default_object_class) > 0:
            tmp_default_object_class = set(default_object_class)
            tmp_default_object_class_db = set(object_class_field.to_db(default_object_class))

        tmp_default_object_class = tmp_default_object_class | set(object_class_field.clean(default_object_class_db))
        tmp_default_object_class_db = tmp_default_object_class_db | set(default_object_class_db)

        default_object_class = list(tmp_default_object_class)
        default_object_class_db = list(tmp_default_object_class_db)

        # start with an empty dictionary
        moddict = {
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
                value = default_object_class_db
                setattr(self, name, default_object_class)
            # otherwise just convert value
            else:
                value = field.to_db(value)
            # db value should always be a list
            assert isinstance(value, list)
            # if dn attribute given, it must match the dn
            if name == dn0k.lower():
                if dn0v.lower() not in set(v.lower() for v in value):
                    raise ValueError("value of %r is %r does not include %r from dn %r"%(name, value, dn0v, self._dn))
            moddict[name] = value
        return moddict

    def _add(self, using):
        # objectClass = attribute + class meta setup
        default_object_class = getattr(self, "objectClass", [])
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

        # objectClass = attribute + class meta setup
        default_object_class = getattr(self, "objectClass", [])
        default_object_class_db = list(self._meta.object_classes)

        # dictionary of old values
        modold = {
        }

        # generate modold values
        fields = self._meta.fields
        for field in fields:
            name = field.name
            modold[name] = self._db_values[using].get(name, [])

        # generate moddict values
        moddict = self._get_moddict(default_object_class, default_object_class_db, using)

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

    def rename(self, using=None, **kwargs):
        """
        Rename this entry. Use like object.rename(uid="new") or
        object.rename(cn="new"). Can pass a list in using, as all
        connections must be renamed at once.
        """

        # extract key and value from kwargs
        assert len(kwargs)==1
        name,value = kwargs.iteritems().next()

        # get the new field and turn value into db value
        field = self._meta.get_field_by_name(name)
        value = field.value_to_db(value)

        # work out the new rdn of the object
        split_new_rdn = [[(name, value, 1)]]
        new_rdn = ldap.dn.dn2str(split_new_rdn)

        # replace cache, any connections not
        # renamed get discarded.
        old_cache = self._db_values
        self._db_values = { }

        # set using if not already set
        using = using or self._alias or tldap.DEFAULT_LDAP_ALIAS

        # turn using into a list if it isn't
        if not isinstance(using, list):
            using = [ using ]

        # what database should we be using?
        for u in using:
            self._db_values[u] = old_cache[u]
            self._rename(new_rdn, u)

        # old cache no longer needed
        old_cache = None

        # construct new dn
        split_dn = ldap.dn.str2dn(self._dn)
        tmplist = []
        tmplist.append(split_new_rdn[0])
        tmplist.extend(split_dn[1:])
        self._dn = ldap.dn.dn2str(tmplist)

    rename.alters_data = True

    def _rename(self, new_rdn, using):
        """
        Low level rename to new_rdn for the using connection.  Works with and
        without cached information for the connection. Doesn't update the
        dn unless operation is reversed during a commit.
        """
        c = tldap.connections[using]

        # what to do if transaction is reversed
        if using in self._db_values:
            # we need to reset cached data and the dn
            old_dn = self._dn
            old_values = self._db_values[using]
            def onfailure():
                self._dn = old_dn
                self._db_values[using] = old_values
        else:
            # no cached data, reset the dn however
            old_dn = self._dn
            def onfailure():
                self._dn = old_dn

        # do the rename
        c.rename(self._dn, new_rdn, onfailure)

        # do we have cached data to update?
        if using in self._db_values:
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
                if old_value in v:
                    v.remove(old_value)
            elif old_value == v:
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
                if new_value not in v:
                    v.append(new_value)
            elif v != new_value:
                # we can't add a value to a string
                assert False
            self._db_values[using][new_key] = field.to_db(v)
            setattr(self, new_key, v)

    _rename.alters_data = True
