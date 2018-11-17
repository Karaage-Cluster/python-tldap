Getting Started
===============
As tldap is a library for use for applications, this documentation
is aimed at Django developers, who are already reasonable competent
at programming with Django.

Basic Usage
-----------
#.  (Django only) Add the following to the django settings file:

    ..  code-block:: python

        LDAP = {
             'default': {
                  'ENGINE': 'tldap.backend.fake_transactions',
                  'URI': 'ldap://localhost',
                  'USER': 'cn=admin,dc=example,dc=org',
                  'PASSWORD': 'XXXXXXXX',
                  'REQUIRE_TLS': False,
                  'START_TLS': False,
                  'TLS_CA' : None,
             }
        }

        INSTALLED_APPS += (
            'tldap.django'
        )

    The database model in Django allows automatically generating uidNumber and gidNumber values, and also automatically
    configures the backends.

#.  (No Django) Initialize tldap with:

    ..  code-block:: python

        import tldap.backends

        settings = {
             'default': {
                  'ENGINE': 'tldap.backend.fake_transactions',
                  'URI': 'ldap://localhost',
                  'USER': 'cn=admin,dc=example,dc=org',
                  'PASSWORD': 'XXXXXXXX',
                  'REQUIRE_TLS': False,
                  'START_TLS': False,
                  'TLS_CA' : None,
             }
        }

        tldap.backends.setup(settings)

#.  Create an application specific layer with LDAP schema information.
    See ``tests/database.py`` and ``tests/django/database.py`` for examples.

#.  Create an object:

    ..  code-block:: python

        account = Account({
            'uid': "tux",
            'givenName': "Tux",
            'sn': "Torvalds",
            'cn': "Tux Torvalds",
            'telephoneNumber': "000",
            'mail': "tuz@example.org",
            'o': "Linux Rules",
            'userPassword': "silly",
            'homeDirectory': "/home/tux",
            'gidNumber': 10,
            'uidNumber': 10,  # Not required if using Django helper method.
        })

        account = tldap.database.insert(account)

#.  Retrieve one object:

    ..  code-block:: python

        account = tldap.database.get_one(Account, Q(uid='tux'))

#.  Search for objects.

    ..  code-block:: python

        for account in tldap.database.search(Account):
            print account["cn"]

#.  For some real examples on how methods are used, see the `karaage
    <https://github.com/Karaage-Cluster/karaage>`_.
