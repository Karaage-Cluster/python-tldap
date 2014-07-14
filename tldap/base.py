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

""" Contains base class used for tldap objects. """
import six

import tldap
import tldap.options
import tldap.exceptions
import tldap.manager
import tldap.fields
import tldap.modlist
import tldap.dn

import ldap3.core.exceptions

import copy

_default_object_class_field = tldap.fields.CharField(required=True,
                                                     max_instances=None)


class LDAPmeta(type):
    """ The meta class used for tldap objects. """

    def __new__(cls, name, bases, attrs):
        super_new = super(LDAPmeta, cls).__new__
        parents = [b for b in bases if isinstance(b, LDAPmeta)]
        if not parents:
            # If this isn't a subclass of LDAPobject, don't do anything special
            return super_new(cls, name, bases, attrs)

        # create new class
        module = attrs.pop('__module__')
        new_class = super_new(cls, name, bases, {'__module__': module})

        # get the attributes to add
        attr_meta = attrs.pop('Meta', None)
        meta = attr_meta
        base_meta = getattr(new_class, '_meta', None)

        # add the _meta and objectClass to new class
        new_class.add_to_class('_meta', tldap.options.Options(meta))
        new_class.add_to_class('objectClass', _default_object_class_field)

        # inherit certain attributes from parent
        if base_meta is not None:
            if new_class._meta.base_dn is None:
                new_class._meta.base_dn = base_meta.base_dn
            if new_class._meta.base_dn_setting is None:
                new_class._meta.base_dn_setting = base_meta.base_dn_setting
            if new_class._meta.pk is None:
                new_class._meta.pk = base_meta.pk

        # create the default manager
        manager = tldap.manager.Manager()
        new_class.add_to_class('objects', manager)
        new_class.add_to_class('_default_manager', manager)

        # add exceptions to the class
        ObjectDoesNotExist = tldap.exceptions.ObjectDoesNotExist
        p = tuple(x.DoesNotExist
                  for x in parents if hasattr(x, '_meta'))
        p = p or (ObjectDoesNotExist,)
        new_class.add_to_class('DoesNotExist', subclass_exception(
            'tldap.exceptions.DoesNotExist', p, module))

        MultipleObjectsReturned = tldap.exceptions.MultipleObjectsReturned
        p = tuple(x.MultipleObjectsReturned
                  for x in parents if hasattr(x, '_meta'))
        p = p or (MultipleObjectsReturned,)
        new_class.add_to_class('MultipleObjectsReturned', subclass_exception(
            'MultipleObjectsReturned', p, module))

        ObjectAlreadyExists = tldap.exceptions.ObjectAlreadyExists
        p = tuple(x.MultipleObjectsReturned
                  for x in parents if hasattr(x, '_meta'))
        p = p or (ObjectAlreadyExists,)
        new_class.add_to_class('AlreadyExists', subclass_exception(
            'ObjectAlreadyExists', p, module))

        p = None

        # get schemas used
        schema_list = attrs.pop('schema_list', [])

        # add rest of attributes to class
        for obj_name, obj in six.iteritems(attrs):
            new_class.add_to_class(obj_name, obj)

        # list of field names
        field_names = new_class._meta.get_all_field_names()

        # check for clashes with reserved names
        for i in ["_db_values", "forcew_replace",
                  "dn", "_dn", "base_dn", "_base_dn", ]:
            if i in field_names:
                raise tldap.exceptions.FieldError(
                    'Local field %s clashes with '
                    'reserved name from base class %r' % (i, name))

        # for every parent ...
        parent_field_names = dict()
        for base in parents + schema_list:
            if not hasattr(base, '_meta'):
                # Things without _meta aren't functional models, so they're
                # uninteresting parents.
                continue

            # for every field in every parent ...
            parent_fields = base._meta.fields
            for field in parent_fields:
                # check if this field from this parent clashes
                if field.name in field_names:
                    # this field already defined in the current class, skip it
                    pass
                elif field.name in attrs:
                    # an attribute in this class has replaced the field
                    pass
                elif field.name in parent_field_names:
                    field_type = type(field)
                    parent_field_type = type(parent_field_names[field.name])
                    if field_type != parent_field_type:
                        raise tldap.exceptions.FieldError(
                            'In class %r field %r from parent clashes '
                            'with field of similar name from base class %r '
                            'and is different type' %
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


class LDAPobject(six.with_metaclass(LDAPmeta)):
    """ The base class used for tldap objects. """

    schema_list = []
    """ Class variable to be overriden for class that provides a list of
    schemas to be used. """

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

    def __init__(self, using=None, settings=None, **kwargs):
        if using is None:
            using = tldap.DEFAULT_LDAP_ALIAS

        self._db_values = None
        self._alias = using
        self._settings = settings
        self._dn = None
        self._base_dn = None
        self.force_replace = set()

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
            raise TypeError(
                "'%s' is an invalid keyword argument for this function" % key)

        if self._dn is not None and self._base_dn is not None:
            raise ValueError("Makes no sense to set both dn and base_dn")

        if self._dn is None and self._base_dn is None:
            self._base_dn = self._meta.base_dn

    @classmethod
    def get_default_base_dn(cls, using, settings):
        """ Get the default base_dn for this *class*.

        :param cls: This class.
        :param using: The LDAP database alias.
        :param settings: A set of parameters that may be useful in derived
            classes.
        :return: Fully qualified base dn. May be None if unsuccessful.
        """

        assert using is not None
        base_dn = cls._meta.base_dn
        if base_dn is None:
            key = cls._meta.base_dn_setting
            if key is not None:
                connection = tldap.connections[using]
                if key in connection.settings_dict:
                    base_dn = connection.settings_dict[key]
        return base_dn

    def _rdn_to_dn(self, name):
        """ Convert the rdn to a fully qualified DN for the specified LDAP
        connection.

        :param self: rdn belongs to this tldap object.
        :param name: rdn to convert.
        :return: fully qualified DN.
        """
        value = getattr(self, name)
        if value is None:
            raise tldap.exceptions.ValidationError(
                "Cannot use %s in dn as it is None" % name)
        if isinstance(value, list):
            raise tldap.exceptions.ValidationError(
                "Cannot use %s in dn as it is a list" % name)

        base_dn = self._base_dn
        if base_dn is None:
            using = self._alias
            assert using is not None
            base_dn = self.get_default_base_dn(using, self._settings)
        assert base_dn is not None

        split_base = tldap.dn.str2dn(base_dn)
        split_new_dn = [[(name, value, 1)]] + split_base

        new_dn = tldap.dn.dn2str(split_new_dn)

        return new_dn

    def save(self, force_add=False, force_modify=False):
        """
        Saves the current instance. Override this in a subclass if you want to
        control the saving process.

        :param self: object to save.
        :param force_add: Assume object doesn't already exist and must be
            created.
        :param force_modify: Assume oobject already exists and must be updated.
        """

        # what database should we be using?
        using = self._alias
        assert using is not None

        if self._dn is None and self._meta.pk is not None:
            self._dn = self._rdn_to_dn(self._meta.pk)

        if self._dn is None:
            raise tldap.exceptions.ValidationError(
                "Need a full DN for this object")

        if force_add and force_modify:
            raise ValueError(
                "Cannot force both insert and updating in model saving.")

        if force_add:
            self._add()
        elif force_modify:
            self._modify()
        elif self._db_values is not None:
            self._modify()
        else:
            self._add()

    save.alters_data = True

    def delete(self):
        """ Delete this object from the LDAP server.

        :param self: object to delete.
        """
        self._delete()
    delete.alters_data = True

    def _get_moddict(self):
        dn0k, dn0v, _ = tldap.dn.str2dn(self._dn)[0][0]

        # objectClass = attribute + class meta setup
        default_object_class = getattr(self, "objectClass", [])
        default_object_class += list(self._meta.object_classes)

        # remove duplicate classes
        default_object_class = list(set(default_object_class))

        for v in default_object_class:
            assert isinstance(v, six.string_types)

        # start with an empty dictionary
        moddict = {
        }

        # generate moddict values
        fields = self._meta.fields
        for field in fields:
            name = field.name
            value = getattr(self, name)

            # if dn attribute not given, try to set it, otherwise just convert
            # value
            if name.lower() == dn0k.lower():
                if isinstance(value, list) and len(value) == 0:
                    value = [dn0v]
                    setattr(self, name, value)
                elif value is None:
                    value = dn0v
                    setattr(self, name, value)

                # value_set, set of all values, lowercase
                if isinstance(value, list):
                    value_set = set(v.lower() for v in value)
                else:
                    value_set = set([value.lower()])

                # dn attribute must match the dn
                if dn0v.lower() not in value_set:
                    raise ValueError(
                        "value of %r is %r does not include %r from dn %r" %
                        (name, value, dn0v, self._dn))

            # if objectClass not given, try to set it, otherwise just convert
            # value
            elif name.lower() == 'objectclass':
                assert isinstance(value, list)
                value = default_object_class
                setattr(self, name, default_object_class)

            # db value should always be a list
            value = field.to_db(value)
            assert isinstance(value, list)
            moddict[name] = value
        return moddict

    def _add(self):
        # generate moddict values
        moddict = self._get_moddict()

        # turn moddict into a modlist
        modlist = tldap.modlist.addModlist(moddict)

        # what database should we be using?
        using = self._alias
        assert using is not None
        c = tldap.connections[using]

        # what to do if transaction is reversed
        def onfailure():
            self._alias = None
            self._db_values = None

        # do it
        try:
            c.add(self._dn, modlist, onfailure)
        except ldap3.core.exceptions.LDAPEntryAlreadyExistsResult:
            raise self.AlreadyExists(
                "Object with dn %r already exists doing add" % (self._dn,))

        # save new values
        self._alias = using
        self._db_values = tldap.helpers.CaseInsensitiveDict(moddict)

    _add.alters_data = True

    def _modify(self):
        fields = self._meta.fields

        # what database should we be using?
        using = self._alias
        assert using is not None
        c = tldap.connections[using]

        # dictionary of old values
        modold = {
        }

        # generate modold values
        fields = self._meta.fields
        for field in fields:
            name = field.name
            modold[name] = self._db_values.get(name, [])

        # generate moddict values
        moddict = self._get_moddict()

        # remove items in force_replace
        force_value = {}
        for field in self.force_replace:
            force_value[field] = moddict[field]
            del modold[field]
            del moddict[field]
        self.force_replace = set()

        # turn moddict into a modlist
        modlist = tldap.modlist.modifyModlist(modold, moddict)

        # FIXME: recheck
        # add items in force_replace
        force_modlist = {}
        for field, value in six.iteritems(force_value):
            force_modlist[field] = (
                ldap3.MODIFY_REPLACE, tldap.modlist.escape_list(value))
            moddict[field] = value

        # what to do if transaction is reversed
        old_values = self._db_values

        def onfailure():
            self._db_values = old_values

        # do it
        if len(modlist) > 0:
            try:
                c.modify(self._dn, modlist, onfailure)
            except ldap3.core.exceptions.LDAPNoSuchObjectResult:
                raise self.DoesNotExist(
                    "Object with dn %r doesn't already exist doing modify" %
                    (self._dn,))

        # we can't rollback these values
        if len(force_modlist) > 0:
            try:
                c.modify_no_rollback(self._dn, force_modlist)
            except ldap3.core.exceptions.LDAPNoSuchObjectResult:
                raise self.DoesNotExist(
                    "Object with dn %r doesn't already exist doing modify" %
                    (self._dn,))

        # save new values
        self._db_values = tldap.helpers.CaseInsensitiveDict(moddict)

    _modify.alters_data = True

    def rename(self, new_base_dn=None, **kwargs):
        """
        Rename this entry. Use like object.rename(uid="new") or
        object.rename(cn="new"). Can pass a list in using, as all
        connections must be renamed at once.

        :param self: object to rename.
        :param new_base_dn: move entry to this parent.
        :param kwargs: Contains new rdn of object.
        """

        # extract key and value from kwargs
        if len(kwargs) == 1:
            name, value = list(six.iteritems(kwargs))[0]

            # replace pk with the real attribute
            if name == "pk":
                name = self._meta.pk

            # work out the new rdn of the object
            split_new_rdn = [[(name, value, 1)]]
        elif len(kwargs) == 0:
            split_new_rdn = [tldap.dn.str2dn(self._dn)[0]]
        else:
            assert False

        new_rdn = tldap.dn.dn2str(split_new_rdn)

        # set using if not already set
        using = self._alias
        assert using is not None

        # turn using into a list if it isn't
        if not isinstance(using, list):
            using = [using]

        # what database should we be using?
        self._rename(new_rdn, new_base_dn)

        # construct new dn
        split_dn = tldap.dn.str2dn(self._dn)
        tmplist = []
        tmplist.append(split_new_rdn[0])
        tmplist.extend(split_dn[1:])
        self._dn = tldap.dn.dn2str(tmplist)

    rename.alters_data = True

    def _rename(self, new_rdn, new_base_dn):
        """
        Low level rename to new_rdn for the using connection.  Works with and
        without cached information for the connection. Doesn't update the
        dn unless operation is reversed during a commit.
        """
        using = self._alias
        assert using is not None
        c = tldap.connections[using]

        # what to do if transaction is reversed
        # we need to reset cached data and the dn
        old_dn = self._dn
        old_values = self._db_values

        def onfailure():
            self._dn = old_dn
            self._db_values = old_values

        # do the rename
        c.rename(self._dn, new_rdn, new_base_dn, onfailure)

        # get old rdn values
        split_old_dn = tldap.dn.str2dn(self._dn)
        old_key, old_value, _ = split_old_dn[0][0]

        # get new rdn values
        split_new_rdn = tldap.dn.str2dn(new_rdn)
        new_key, new_value, _ = split_new_rdn[0][0]

        # make a copy before modifications
        self._db_values = copy.deepcopy(self._db_values)

        # delete old rdn attribute in object
        old_key = self._meta.get_field_name(old_key)
        field = self._meta.get_field_by_name(old_key)
        v = getattr(self, old_key, [])
        if v is None:
            pass
        elif isinstance(v, list):
            if old_value in v:
                v.remove(old_value)
        elif old_value == v:
            v = None
        if v is None:
            del self._db_values[old_key]
        elif isinstance(v, list) and len(v) == 0:
            del self._db_values[old_key]
        else:
            self._db_values[old_key] = field.to_db(v)
        setattr(self, old_key, v)

        # update new rdn attribute in object
        new_key = self._meta.get_field_name(new_key)
        field = self._meta.get_field_by_name(new_key)
        v = getattr(self, new_key, None)
        if v is None:
            v = new_value
        elif isinstance(v, list):
            if new_value not in v:
                v.append(new_value)
        elif v != new_value:
            # we can't add a value to a string
            assert False
        self._db_values[new_key] = field.to_db(v)
        setattr(self, new_key, v)

    _rename.alters_data = True

    def _delete(self):
        # what database should we be using?
        using = self._alias
        assert using is not None
        c = tldap.connections[using]

        # what to do if transaction is reversed
        old_values = self._db_values

        def onfailure():
            self._db_values = old_values

        # delete it
        c.delete(self._dn, onfailure)
        self._db_values = None
    _delete.alters_data = True

    def unparse(self, ldif_writer, new_dn=None, extra_fields={}):
        """ Translate object into ldif.

        :param self: object to translate.
        :param ldif_writer: ldif_writer to write translation to.
        :param extra_fields: extra fields to display
        """

        # generate moddict values
        moddict = self._get_moddict()
        moddict.update(extra_fields)

        if new_dn is not None:
            dn = new_dn
        else:
            dn = self.dn

        # do stuff
        return ldif_writer.unparse(dn, moddict)
