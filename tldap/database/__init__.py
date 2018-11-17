# Copyright 2018 Brian May
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

""" High level database interaction. """
from typing import List, Iterator, TypeVar, Optional, Type, Set, Tuple

import ldap3.core
import ldap3.core.exceptions

import tldap.fields
from tldap import Q

from tldap.backend.base import LDAPbase
from tldap.dict import ImmutableDict
from tldap.dn import dn2str, str2dn
from tldap.exceptions import ObjectAlreadyExists, ObjectDoesNotExist, MultipleObjectsReturned
import tldap.query


class SearchOptions:
    """ Application specific search options. """
    def __init__(self, base_dn: str, object_class: Set[str], pk_field: str) -> None:
        self.base_dn = base_dn
        self.object_class = object_class
        self.pk_field = pk_field


LdapObjectEntity = TypeVar('LdapObjectEntity', bound='LdapObject')
LdapObjectClass = Type['LdapObject']


class LdapObject(ImmutableDict):
    """ A high level python representation of a LDAP object. """

    def __init__(self, d: Optional[dict]=None) -> None:
        fields = self.get_fields()
        field_names = set(f.name for f in fields)

        python_data = {
            field_name: None
            for field_name in field_names
        }
        if d is not None:
            python_data.update(d)

        super().__init__(field_names, python_data)

    @classmethod
    def get_fields(cls) -> List[tldap.fields.Field]:
        raise NotImplementedError()

    @classmethod
    def get_search_options(cls, settings: dict) -> SearchOptions:
        raise NotImplementedError()

    @classmethod
    def on_load(cls, python_data: 'LdapObject', settings: dict) -> 'LdapObject':
        raise NotImplementedError()

    @classmethod
    def on_save(cls, changes: 'LdapChanges', settings: dict) -> 'LdapChanges':
        raise NotImplementedError()

    def __copy__(self: LdapObjectEntity) -> LdapObjectEntity:
        return self.__class__(self._dict)


LdapChangesEntity = TypeVar('LdapChangesEntity', bound='LdapChanges')


class LdapChanges(ImmutableDict):
    """ Represents a set of changes to an LdapObject. """

    def __init__(self, fields: List[tldap.fields.Field], src: LdapObject, d: Optional[dict]=None) -> None:
        self._fields = fields
        self._src = src
        field_names = set(f.name for f in fields)
        super().__init__(field_names, d)

    def __copy__(self: LdapChangesEntity) -> LdapChangesEntity:
        return self.__class__(self._fields, self._src, self._dict)

    def _set(self, key: str, value: any) -> None:
        previous_value = self._src[key]
        if value != previous_value:
            self._dict[key] = value
        elif key in self._dict:
            del self._dict[key]
        return

    @property
    def src(self) -> LdapObject:
        return self._src


DbDataEntity = TypeVar('DbDataEntity', bound='DbData')


class DbData(ImmutableDict):
    """ Represents an LDAP object at low level without any translations. """

    def __init__(self, fields: List[tldap.fields.Field], d: Optional[dict]=None) -> None:
        self._fields = fields
        field_names = set(f.name for f in fields if f.db_field)
        super().__init__(field_names, d)

    def __copy__(self: DbDataEntity) -> DbDataEntity:
        return self.__class__(self._fields, self._dict)


DbChangesEntity = TypeVar('DbChangesEntity', bound='DbChanges')


class DbChanges(ImmutableDict):
    """ Represents an set of changes to an LDAP object at low level without any translations. """

    def __init__(self, fields: List[tldap.fields.Field], d: Optional[dict]=None) -> None:
        self._fields = fields
        field_names = set(f.name for f in fields if f.db_field)
        super().__init__(field_names, d)

    def __copy__(self: DbChangesEntity) -> DbChangesEntity:
        return self.__class__(self._fields, self._dict)


class NotLoaded:
    """ Base class to represent a related field that has not been loaded. """

    def __repr__(self):
        raise NotImplementedError()

    def load(self, connection_key: str='default') -> LdapObject or List[LdapObject]:
        raise NotImplementedError()

    @staticmethod
    def _load_one(table: LdapObjectClass, key: str, value: str, connection_key: str='default') -> LdapObject:
        q = Q(**{key: value})
        result = get_one(table, q, connection_key)
        return result

    @staticmethod
    def _load_list(table: LdapObjectClass, key: str, value: str, connection_key: str='default') -> List[LdapObject]:
        q = Q(**{key: value})
        return list(search(table, q, connection_key))


class NotLoadedObject(NotLoaded):
    """ Represents a single object that needs to be loaded. """
    def __init__(self, *, table: LdapObjectClass, key: str, value: str):
        self._table = table
        self._key = key
        self._value = value

    def __repr__(self):
        return f"<NotLoaded {self._table} {self._key}={self._value}>"

    def load(self, connection_key: str='default') -> LdapObject:
        return self._load_one(self._table, self._key, self._value)


class NotLoadedList(NotLoaded):
    """ Represents a list of objects that needs to be loaded via a single key. """

    def __init__(self, *, table: LdapObjectClass, key: str, value: str):
        self._table = table
        self._key = key
        self._value = value

    def __repr__(self):
        return f"<NotLoaded {self._table} {self._key}={self._value}>"

    def load(self, connection_key: str='default') -> List[LdapObject]:
        return self._load_list(self._table, self._key, self._value, connection_key)


class NotLoadedListToList(NotLoaded):
    """ Represents a list of objects that needs to be loaded via a list of key values. """

    def __init__(self, *, table: LdapObjectClass, key: str, value: List[str]):
        self._table = table
        self._key = key
        self._value = value

    def __repr__(self):
        return f"<NotLoadedList {self._table} {self._key}={self._value}>"

    def load(self, connection_key: str='default') -> List[LdapObject]:
        result = [
            self._load_one(self._table, self._key, value, connection_key)
            for value in self._value
        ]
        result = [value for value in result if value is not None]
        return result


def get_changes(python_data: LdapObject, d: dict) -> LdapChanges:
    """ Generate changes object for ldap object. """
    table: LdapObjectClass = type(python_data)
    fields = table.get_fields()

    changes = LdapChanges(fields, src=python_data, d=d)
    return changes


def _db_to_python(db_data: DbData, table: LdapObjectClass, dn: str) -> LdapObject:
    """ Convert a DbDate object to a LdapObject. """
    fields = table.get_fields()

    python_data = table({
        field.name: field.to_python(db_data[field.name])
        for field in fields
        if field.db_field
    })
    python_data = python_data.merge({
        'dn': dn,
    })
    return python_data


def _python_to_db(changes: LdapChanges) -> DbChanges:
    """ Convert a LdapChanges object to a DbChanges object. """
    table: LdapObjectClass = type(changes.src)
    fields = table.get_fields()

    db_changes_dict = {
        field.name: field.to_db(changes[field.name])
        for field in fields
        if field.name in changes and field.db_field
    }

    db_changes = DbChanges(fields, db_changes_dict)
    return db_changes


def search(table: LdapObjectClass, query: Optional[Q]=None, connection_key: str='default', base_dn: Optional[str]=None) -> Iterator[LdapObject]:
    """ Search for a object of given type in the database. """
    fields = table.get_fields()
    db_fields = [field for field in fields if field.db_field]
    connection = tldap.backend.connections[connection_key]
    settings = connection.settings_dict

    search_options = table.get_search_options(settings)

    iterator = tldap.query.search(
        connection=connection,
        query=query,
        fields=db_fields,
        base_dn=base_dn or search_options.base_dn,
        object_classes=search_options.object_class,
        pk=search_options.pk_field,
    )

    for dn, data in iterator:
        db_data = DbData(fields, data)
        python_data = _db_to_python(db_data, table, dn)
        python_data = table.on_load(python_data, settings)
        yield python_data


def get_one(table: LdapObjectClass, query: Q, connection_key: str='default', base_dn: Optional[str]=None) -> LdapObject:
    """ Get exactly one result from the database or fail. """
    results = search(table, query, connection_key, base_dn)

    try:
        result = next(results)
    except StopIteration:
        raise ObjectDoesNotExist()

    try:
        next(results)
        raise MultipleObjectsReturned()
    except StopIteration:
        pass

    return result


def preload(python_data: LdapObject, connection_key: str='default') -> LdapObject:
    """ Preload all NotLoaded fields in LdapObject. """
    table: LdapObjectClass = type(python_data)
    fields = table.get_fields()

    changes = {
        field.name: python_data[field.name].load(connection_key)
        for field in fields
        if isinstance(python_data[field.name], NotLoaded)
    }

    return python_data.merge(changes)


def insert(python_data: LdapObject, connection_key: str='default') -> LdapObject:
    """ Insert a new python_data object in the database. """
    assert isinstance(python_data, LdapObject)
    assert python_data['dn'] is None

    table: LdapObjectClass = type(python_data)

    # ADD NEW ENTRY
    empty_data = table()
    changes = get_changes(empty_data, python_data.to_dict())

    return save(changes, connection_key)


def _get_mod(value: List[bytes]) -> Tuple[str, List[bytes]]:
    """ Get the LDAP operation for this value. """
    if len(value) == 0:
        return ldap3.MODIFY_DELETE, []
    else:
        return ldap3.MODIFY_REPLACE, value


def save(changes: LdapChanges, connection_key: str='default') -> LdapObject:
    """ Save all changes in a LdapChanges. """
    assert isinstance(changes, LdapChanges)

    connection = tldap.backend.connections[connection_key]
    settings = connection.settings_dict

    table = type(changes._src)

    # Run hooks on changes
    changes = table.on_save(changes, settings)

    # src dn   | changes dn | result         | action
    # ---------------------------------------|--------
    # None     | None       | error          | error
    # None     | provided   | use changes dn | create
    # provided | None       | use src dn     | modify
    # provided | provided   | error          | error

    if changes.src['dn'] is None and 'dn' not in changes:
        raise RuntimeError("No DN was given")
    elif changes.src['dn'] is None and 'dn' in changes:
        dn = changes['dn']
        assert dn is not None
        create = True
    elif changes.src['dn'] is not None and 'dn' not in changes:
        dn = changes.src['dn']
        assert dn is not None
        create = False
    else:
        raise RuntimeError("Changes to DN are not supported.")

    assert dn is not None

    # Generate DB changes.
    db_changes = _python_to_db(changes)

    if create:
        # Add new entry
        mod_list = {
            name: value
            for name, value in db_changes.items()
            if len(value) > 0
        }
        try:
            connection.add(dn, mod_list)
        except ldap3.core.exceptions.LDAPEntryAlreadyExistsResult:
            raise ObjectAlreadyExists(
                "Object with dn %r already exists doing add" % dn)
    else:
        # Modify existing entry.
        mod_list = {
            name: _get_mod(value)
            for name, value in db_changes.items()
        }
        if len(mod_list) > 0:
            try:
                connection.modify(dn, mod_list)
            except ldap3.core.exceptions.LDAPNoSuchObjectResult:
                raise ObjectDoesNotExist(
                    "Object with dn %r doesn't already exist doing modify" % dn)

    # get new values
    python_data = table(changes.src.to_dict())
    python_data = python_data.merge(changes.to_dict())
    python_data = python_data.on_load(python_data, settings)
    return python_data


def delete(python_data: LdapObject, connection_key: str='default') -> None:
    """ Delete a LdapObject from the database. """
    dn = python_data['dn']
    assert dn is not None
    connection = tldap.backend.connections[connection_key]
    connection.delete(dn)


def get_field_by_name(table: LdapObjectClass, name: str) -> tldap.fields.Field:
    """ Lookup a field by its name. """
    fields = table.get_fields()
    f = [field for field in fields if field.name == name]
    if len(f) < 0:
        raise ValueError("Cannot find field %s " % name)
    return f[0]


def rename(python_data: LdapObject, new_base_dn=None, connection_key: str='default', **kwargs) -> LdapObject:
    """ Move/rename a LdapObject in the database. """
    table = type(python_data)
    dn = python_data['dn']
    assert dn is not None
    connection = tldap.backend.connections[connection_key]

    # extract key and value from kwargs
    if len(kwargs) == 1:
        name, value = list(kwargs.items())[0]

        # work out the new rdn of the object
        split_new_rdn = [[(name, value, 1)]]

        field = get_field_by_name(table, name)
        assert field.db_field

        python_data = python_data.merge({
            name: value,
        })

    elif len(kwargs) == 0:
        split_new_rdn = [str2dn(dn)[0]]
    else:
        assert False

    new_rdn = dn2str(split_new_rdn)

    connection.rename(
        dn,
        new_rdn,
        new_base_dn,
    )

    if new_base_dn is not None:
        split_base_dn = str2dn(new_base_dn)
    else:
        split_base_dn = str2dn(dn)[1:]

    tmp_list = [split_new_rdn[0]]
    tmp_list.extend(split_base_dn)

    new_dn = dn2str(tmp_list)

    python_data = python_data.merge({
        'dn': new_dn,
    })
    return python_data
