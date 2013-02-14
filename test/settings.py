
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'placard',
    'placard.lusers',
    'placard.lgroups',
    'andsome',
    'andsome.layout',
)

LDAP = {
    'default': {
        'ENGINE': 'tldap.backend.transaction',
        'URI': 'ldap://localhost:38911/',
        'USER': 'cn=Manager,dc=python-ldap,dc=org',
        'PASSWORD': 'password',
        'USE_TLS': False,
        'TLS_CA' : None,
        'LDAP_ACCOUNT_BASE': 'ou=People, dc=python-ldap,dc=org',
        'LDAP_GROUP_BASE': 'ou=Group, dc=python-ldap,dc=org'
    }
}

TEST_RUNNER='andsome.test_utils.xmlrunner.run_tests'
DATABASE_ENGINE = 'sqlite3'

ROOT_URLCONF = 'demo.urls'

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'andsome.middleware.threadlocals.ThreadLocals',
    'django.middleware.doc.XViewMiddleware',
)
