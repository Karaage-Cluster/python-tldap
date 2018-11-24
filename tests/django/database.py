from tldap.database import Changeset, Database
from tests import database as parent


class Account(parent.Account):

    @classmethod
    def on_save(cls, changes: Changeset, database: Database) -> Changeset:
        return changes


class Group(parent.Group):

    @classmethod
    def on_save(cls, changes: Changeset, database: Database) -> Changeset:
        return changes