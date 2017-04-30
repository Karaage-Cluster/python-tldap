import mock
import pytest

import tldap


@pytest.fixture
def LDAP():
    LDAP = {
        'default': {
            'ENGINE': 'tldap.backend.fake_transactions',
            'URI': 'ldap://localhost:38911/',
            'USER': 'cn=Manager,dc=python-ldap,dc=org',
            'PASSWORD': 'password',
            'USE_TLS': False,
            'TLS_CA': None,
            'LDAP_ACCOUNT_BASE': 'ou=People, dc=python-ldap,dc=org',
            'LDAP_GROUP_BASE': 'ou=Group, dc=python-ldap,dc=org'
        }
    }

    tldap.setup(LDAP)
    server = tldap.test.slapd.Slapd()
    server.set_port(38911)

    server.start()

    yield tldap.connection

    server.stop()


@pytest.fixture
def mock_LDAP():
    LDAP = {
        'default': {
            'ENGINE': 'tldap.backend.fake_transactions',
            'URI': 'ldap://localhost:38911/',
            'USER': 'cn=Manager,dc=python-ldap,dc=org',
            'PASSWORD': 'password',
            'USE_TLS': False,
            'TLS_CA': None,
            'LDAP_ACCOUNT_BASE': 'ou=People, dc=python-ldap,dc=org',
            'LDAP_GROUP_BASE': 'ou=Group, dc=python-ldap,dc=org'
        }
    }
    tldap.setup(LDAP)
    connection = mock.Mock()
    connection.settings_dict = LDAP['default']
    setattr(tldap.connections._connections, 'default', connection)
    return connection
