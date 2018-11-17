import mock
import pytest

import tldap.backend
import tests.database


@pytest.fixture
def mock_ldap():
    ldap = {
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
    tldap.backend.setup(ldap)
    connection = mock.Mock()
    connection.settings_dict = ldap['default']
    setattr(tldap.backend.connections._connections, 'default', connection)
    return connection
