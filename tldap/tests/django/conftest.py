from django.conf import settings
import pytest

import tldap.backend
import tldap.database
import tldap.test.slapd
import tldap.tests.database

@pytest.fixture
def LDAP():
    # Required because over tests will have overwritten these settings.
    tldap.backend.setup(settings.LDAP)

    server = tldap.test.slapd.Slapd()
    server.set_port(38911)

    server.start()

    yield tldap.backend.connections['default']

    server.stop()


@pytest.fixture
def LDAP_ou(LDAP):
    organizational_unit = tldap.tests.database.OU({
        'dn': "ou=People, dc=python-ldap,dc=org"
    })
    tldap.database.insert(organizational_unit)

    organizational_unit = tldap.tests.database.OU({
        'dn': "ou=Groups, dc=python-ldap,dc=org"
    })
    tldap.database.insert(organizational_unit)