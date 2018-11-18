from typing import List

import tldap.fields
from tldap.database import helpers, LdapObject, LdapChanges, SearchOptions, Database
import tldap.django.helpers as dhelpers


class Account(LdapObject):

    @classmethod
    def get_fields(cls) -> List[tldap.fields.Field]:
        fields = []
        fields += helpers.get_fields_common()
        fields += helpers.get_fields_person()
        fields += helpers.get_fields_account()
        fields += helpers.get_fields_shadow()
        fields += helpers.get_fields_pwdpolicy()
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
        python_data = helpers.load_pwdpolicy(python_data)
        return python_data

    @classmethod
    def on_save(cls, changes: LdapChanges, database: Database) -> LdapChanges:
        settings = database.settings
        changes = helpers.save_person(changes)
        changes = helpers.save_account(changes)
        changes = helpers.save_shadow(changes)
        changes = helpers.save_pwdpolicy(changes)
        changes = dhelpers.save_account(changes, Account, database)
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
        changes = dhelpers.save_group(changes, Group, database)
        return changes
