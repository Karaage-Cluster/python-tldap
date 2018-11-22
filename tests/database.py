import os
from typing import List

import tldap.fields
from tldap.database import helpers, LdapObject, LdapChanges, SearchOptions, Database


class Account(LdapObject):

    @classmethod
    def get_fields(cls) -> List[tldap.fields.Field]:
        fields = []
        fields += helpers.get_fields_common()
        fields += helpers.get_fields_person()
        fields += helpers.get_fields_account()
        fields += helpers.get_fields_shadow()

        if os.environ['LDAP_TYPE'] == "openldap":
            fields += helpers.get_fields_pwdpolicy()
        elif os.environ['LDAP_TYPE'] == 'ds389':
            fields += helpers.get_fields_password_object()

        return fields

    @classmethod
    def get_search_options(cls, database: Database) -> SearchOptions:
        settings = database.settings
        return SearchOptions(
            base_dn=settings['LDAP_ACCOUNT_BASE'],
            object_class={'inetOrgPerson', 'organizationalPerson', 'person'},
            pk_field="uid",
        )

    @classmethod
    def on_load(cls, python_data: LdapObject, _database: Database) -> LdapObject:
        python_data = helpers.load_person(python_data, Group)
        python_data = helpers.load_account(python_data, Group)
        python_data = helpers.load_shadow(python_data)

        if os.environ['LDAP_TYPE'] == "openldap":
            python_data = helpers.load_pwdpolicy(python_data)
        elif os.environ['LDAP_TYPE'] == 'ds389':
            python_data = helpers.load_password_object(python_data)

        return python_data

    @classmethod
    def on_save(cls, changes: LdapChanges, database: Database) -> LdapChanges:
        settings = database.settings
        changes = helpers.save_person(changes)
        changes = helpers.save_account(changes, database)
        changes = helpers.save_shadow(changes)

        if os.environ['LDAP_TYPE'] == "openldap":
            changes = helpers.save_pwdpolicy(changes)
        elif os.environ['LDAP_TYPE'] == 'ds389':
            changes = helpers.load_password_object(changes)

        changes = helpers.set_object_class(changes, ['top', 'person', 'inetOrgPerson', 'organizationalPerson',
                                                     'shadowAccount', 'posixAccount', 'pwdPolicy'])
        changes = helpers.rdn_to_dn(changes, 'uid', settings['LDAP_ACCOUNT_BASE'])
        return changes


class Group(LdapObject):

    @classmethod
    def get_fields(cls) -> List[tldap.fields.Field]:
        fields = []
        fields += helpers.get_fields_common()
        fields += helpers.get_fields_group()
        return fields

    @classmethod
    def get_search_options(cls, database: Database) -> SearchOptions:
        settings = database.settings
        return SearchOptions(
            base_dn=settings['LDAP_GROUP_BASE'],
            object_class={'posixGroup'},
            pk_field="cn",
        )

    @classmethod
    def on_load(cls, python_data: LdapObject, _database: Database) -> LdapObject:
        python_data = helpers.load_group(python_data, Account)
        return python_data

    @classmethod
    def on_save(cls, changes: LdapChanges, database: Database) -> LdapChanges:
        settings = database.settings
        changes = helpers.save_group(changes)
        changes = helpers.set_object_class(changes, ['top', 'posixGroup'])
        changes = helpers.rdn_to_dn(changes, 'cn', settings['LDAP_GROUP_BASE'])
        return changes

    @classmethod
    def add_member(cls, changes: LdapChanges, member: 'Account') -> LdapChanges:
        assert isinstance(changes.src, cls)
        return helpers.add_group_member(changes, member)

    @classmethod
    def remove_member(cls, changes: LdapChanges, member: 'Account') -> LdapChanges:
        assert isinstance(changes.src, cls)
        return helpers.remove_group_member(changes, member)


class OU(LdapObject):

    @classmethod
    def get_fields(cls) -> List[tldap.fields.Field]:
        fields = []
        fields += helpers.get_fields_common()
        return fields

    @classmethod
    def get_search_options(cls, database: Database) -> SearchOptions:
        return SearchOptions(
            base_dn="",
            object_class={'organizationalUnit'},
            pk_field="ou",
        )

    @classmethod
    def on_load(cls, python_data: LdapObject, _database: Database) -> LdapObject:
        return python_data

    @classmethod
    def on_save(cls, changes: LdapChanges, _database: Database) -> LdapChanges:
        changes = helpers.set_object_class(changes, ['top', 'organizationalUnit'])
        return changes
