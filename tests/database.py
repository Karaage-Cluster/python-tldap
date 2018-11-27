import os
from typing import Dict

import tldap.fields
from tldap.database import helpers, LdapObject, Changeset, SearchOptions, Database
import tldap.django.helpers as dhelpers


class Account(LdapObject):

    @classmethod
    def get_fields(cls) -> Dict[str, tldap.fields.Field]:
        fields = {
            **helpers.get_fields_common(),
            **helpers.get_fields_person(),
            **helpers.get_fields_account(),
            **helpers.get_fields_shadow(),
        }

        if os.environ['LDAP_TYPE'] == "openldap":
            fields.update(helpers.get_fields_pwdpolicy())
        elif os.environ['LDAP_TYPE'] == 'ds389':
            fields.update(helpers.get_fields_password_object())

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
    def on_load(cls, python_data: LdapObject, database: Database) -> LdapObject:
        python_data = helpers.load_person(python_data, Group)
        python_data = helpers.load_account(python_data, Group)
        python_data = helpers.load_shadow(python_data)

        if os.environ['LDAP_TYPE'] == "openldap":
            python_data = helpers.load_pwdpolicy(python_data)
        elif os.environ['LDAP_TYPE'] == 'ds389':
            python_data = helpers.load_password_object(python_data)

        return python_data

    @classmethod
    def on_save(cls, changes: Changeset, database: Database) -> Changeset:
        settings = database.settings
        changes = helpers.save_person(changes, database)
        changes = helpers.save_account(changes, database)
        changes = helpers.save_shadow(changes)

        classes = ['top', 'person', 'inetOrgPerson', 'organizationalPerson',
                   'shadowAccount', 'posixAccount']

        if os.environ['LDAP_TYPE'] == "openldap":
            changes = helpers.save_pwdpolicy(changes)
            classes = classes + ['pwdPolicy']
        elif os.environ['LDAP_TYPE'] == 'ds389':
            changes = helpers.save_password_object(changes)
            classes = classes + ['passwordObject']

        changes = dhelpers.save_account(changes, Account, database)
        changes = helpers.set_object_class(changes, classes)
        changes = helpers.rdn_to_dn(changes, 'uid', settings['LDAP_ACCOUNT_BASE'])
        return changes


class Group(LdapObject):

    @classmethod
    def get_fields(cls) -> Dict[str, tldap.fields.Field]:
        fields = {
            **helpers.get_fields_common(),
            **helpers.get_fields_group(),
        }
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
    def on_save(cls, changes: Changeset, database: Database) -> Changeset:
        settings = database.settings
        changes = helpers.save_group(changes)
        changes = dhelpers.save_group(changes, Group, database)
        changes = helpers.set_object_class(changes, ['top', 'posixGroup'])
        changes = helpers.rdn_to_dn(changes, 'cn', settings['LDAP_GROUP_BASE'])
        return changes

    @classmethod
    def add_member(cls, changes: Changeset, member: 'Account') -> Changeset:
        assert isinstance(changes.src, cls)
        return helpers.add_group_member(changes, member)

    @classmethod
    def remove_member(cls, changes: Changeset, member: 'Account') -> Changeset:
        assert isinstance(changes.src, cls)
        return helpers.remove_group_member(changes, member)


class OU(LdapObject):

    @classmethod
    def get_fields(cls) -> Dict[str, tldap.fields.Field]:
        fields = helpers.get_fields_common()
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
    def on_save(cls, changes: Changeset, _database: Database) -> Changeset:
        changes = helpers.set_object_class(changes, ['top', 'organizationalUnit'])
        return changes
