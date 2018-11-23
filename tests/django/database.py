from tldap.database import LdapChanges, Database
from tests import database as parent


class Account(parent.Account):

    @classmethod
    def on_save(cls, changes: LdapChanges, database: Database) -> LdapChanges:
        return changes


class Group(parent.Group):

    @classmethod
    def on_save(cls, changes: LdapChanges, database: Database) -> LdapChanges:
        return changes