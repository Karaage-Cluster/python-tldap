from tldap.database import LdapChanges, Database
import tldap.django.helpers as dhelpers
from tests import database as parent


class Account(parent.Account):

    @classmethod
    def on_save(cls, changes: LdapChanges, database: Database) -> LdapChanges:
        changes = parent.Account.on_save(changes, database)
        changes = dhelpers.save_account(changes, Account, database)
        return changes


class Group(parent.Group):

    @classmethod
    def on_save(cls, changes: LdapChanges, database: Database) -> LdapChanges:
        changes = parent.Group.on_save(changes, database)
        changes = dhelpers.save_group(changes, Group, database)
        return changes