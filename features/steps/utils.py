import tldap


def do_config(DN, password):
    LDAP = {
        'default': {
            'ENGINE': 'tldap.backend.fake_transactions',
            'URI': 'ldap://localhost:38911/',
            'USER': DN,
            'PASSWORD': password,
            'USE_TLS': False,
            'TLS_CA': None,
            'LDAP_ACCOUNT_BASE': 'ou=People, dc=python-ldap,dc=org',
            'LDAP_GROUP_BASE': 'ou=Groups, dc=python-ldap,dc=org'
        }
    }

    tldap.setup(LDAP)
    tldap.connection.close()
