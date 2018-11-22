import os

from django.conf import settings
import pytest
from ldap3.core import exceptions

import tldap.backend
import tldap.database


def delete(connection, dn):
    try:
        connection.delete(dn)
    except exceptions.LDAPNoSuchObjectResult:
        pass


@pytest.fixture
def ldap():
    # Required because over tests will have overwritten these settings.
    tldap.backend.setup(settings.LDAP)

    connection = tldap.backend.connections['default']
    yield connection

    delete(connection, f"uid=tux1,{os.environ['LDAP_ACCOUNT_BASE']}")
    delete(connection, f"uid=tux2,{os.environ['LDAP_ACCOUNT_BASE']}")
    delete(connection, f"uid=tux3,{os.environ['LDAP_ACCOUNT_BASE']}")

    delete(connection, f"cn=penguins1,{os.environ['LDAP_GROUP_BASE']}")
    delete(connection, f"cn=penguins2,{os.environ['LDAP_GROUP_BASE']}")
    delete(connection, f"cn=penguins3,{os.environ['LDAP_GROUP_BASE']}")
