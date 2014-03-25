Getting Started
===============
As tldap is a library for use for applications, this documentation
is aimed at Django developers, who are already reasonable compentant
at programming with Django.

Basic Usage
-----------
For basic usage, mysql server is not required.

#.  Add the following to the django settings file:

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

#.  Methods a similar to Django methods. First some imports:

    ..  code-block:: python

        import tldap.schemas.rfc as rfc
        from tldap import Q

#.  For convenience:

    ..  code-block:: python

        manager = rfc.organizationalUnit.objects.db_manager(
            base_dn="dc=something,dc=org")

#.  Create an object:

    ..  code-block:: python

        ou = manager.create(ou="Test")
        ou.l = "North Poll"
        ou.save()

#.  Retrieve one object:

    ..  code-block:: python

        ou = manager.get(ou="Test")

#.  Search for objects.

    ..  code-block:: python

        for ou in manager.all():
            print ou.l

        for ou in manager.all(Q(ou="Test") | Q(l="North Poll")
            print ou.l


Combining Schemas
-----------------
#.  Create object representing combined object

    ..  code-block:: python

        from tldap.schemas import rfc, ad, samba, eduroam, other
        import tldap.manager

        class rfc_account(base.baseMixin):
            schema_list = [
                    rfc.person, rfc.organizationalPerson, rfc.inetOrgPerson,
                    rfc.pwdPolicy, rfc.posixAccount, rfc.shadowAccount,
                    samba.sambaSamAccount, eduroam.eduPerson,
                    eduroam.auEduPerson, other.ldapPublicKey, ]

            class Meta:
                base_dn_setting = "LDAP_ACCOUNT_BASE"
                object_classes = set([ 'top' ])
                search_classes = set([ 'posixAccount' ])
                pk = 'uid'

            managed_by = tldap.manager.ManyToOneDescriptor(this_key='manager',
                linked_cls='full.name.rfc_account', linked_key='dn')
            manager_of = tldap.manager.OneToManyDescriptor(this_key='dn',
                linked_cls='full.name.rfc_account', linked_key='manager')
            unixHomeDirectory = tldap.manager.AliasDescriptor("homeDirectory")

        class rfc_group(base.baseMixin):
            schema_list = [ rfc.posixGroup, samba.sambaGroupMapping, ]

            class Meta:
                base_dn_setting = "LDAP_GROUP_BASE"
                object_classes = set([ 'top' ])
                search_classes = set([ 'posixGroup' ])
                pk = 'cn'

            primary_accounts = tldap.manager.OneToManyDescriptor(
                this_key='gidNumber', linked_cls=rfc_account,
                linked_key='gidNumber', related_name="primary_group")
            secondary_accounts = tldap.manager.ManyToManyDescriptor(
                this_key='memberUid', linked_cls=rfc_account,
                linked_key='uid', linked_is_p=False,
                related_name="secondary_groups")

    The extra fields, ``managed_by``, ``manager_of``, ``unixHomeDirectory``,
    ``primary_accounts``, and ``secondary_accounts`` are for add convenience,
    and to allow modifying these values with a similar interface regardless of
    the ldap schema in use.

#.  This creates a new ``Meta`` class, the possible settings are:

    ..  py:class:: Meta

        ..  py:attribute:: Meta.base_dn

            Reference to default base DN. Used for searching and creating new
            objects.

        ..  py:attribute:: Meta.base_dn_setting

            Reference to the name of a Django LDAP setting that contains
            the base DN.

        ..  py:attribute:: Meta.object_classes

            These object classes are added to every object create. Note
            the default schemas also include object_classes. The final
            list contains all the object_classes combined.

        ..  py:attribute:: Meta.search_classes

            List of object classes to use when conducting searches.

        ..  py:attribute:: Meta.pk

            The name of the atttribute to use for the primary key. The pk
            value is used when creating the dn for new objects. It also
            means that ``object.pk`` is an alias of the real attribute.

#.  Set the new required ``LDAP_ACCOUNT_BASE`` and ``LDAP_GROUP_BASE`` settings
    in your django configuration:

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
                  'LDAP_ACCOUNT_BASE': 'ou=People,dc=example,dc=org',
                  'LDAP_GROUP_BASE': 'ou=group,dc=example,dc=org',
             }
        }

    (this is optional, there is another way of setting these values which
    will be explored later)

#.  Use as before, instead of organizationalUnit.


tldap.methods
-------------
Often the code to manipulate attributes is the same across different projects.
``tldap.methods`` is the module to avoid having to repeat code accross projects.

These require a mysql database for the mysql models. South migrations are
provided.

#.  Add ``tldap.methods`` to ``INSTALLED_APPS`` in the Django settings.

#.  Add ``south`` to ``INSTALLED_APPS`` in the Django settings, if not already
    configured.

#.  Run the south migration.

    ..  code-block:: bash

        ./manage.py migrate

#.  Add some imports:

    ..  code-block:: python

        import tldap.methods as base
        import tldap.methods.common as common
        import tldap.methods.pwdpolicy as pwdpolicy
        import tldap.methods.ad as mad
        import tldap.methods.samba as samba
        import tldap.methods.shibboleth as shibboleth

#.  Add some attributes to the above classes:

    ..  code-block:: python

        class rfc_account(base.baseMixin):
            [...]

            mixin_list = [ common.personMixin, pwdpolicy.pwdPolicyMixin,
                common.accountMixin, common.shadowMixin, samba.sambaAccountMixin,
                shibboleth.shibbolethMixin, localAccountMixin,
                localRfcAccountMixin, ]

            [...]

        class rfc_group(base.baseMixin):
            [...]

            mixin_list = [ common.personMixin, common.accountMixin,
                mad.adUserMixin, localAccountMixin, localAdAccountMixin ]

            [...]

#.  Some of the methods require a mysql database to be setup in Django
    to keep track of the last used uidNumber and gidNumber.

#.  With methods you are required to pass the manager settings. There are
    various ways of doing this:

    ..  code-block:: python

        settings = {
            [...]
        }

        manager = rfc_person(using="default", settings=settings)
        query = manager.using(using="default", settings=settings)
        person = rfc_person(using="default", settings=settings)

    The list of settings available depends on which mixin you use.


    *   All:

        *   The :py:attr:`Meta.base_dn_setting`, described above. If the
            referred setting is not in the global settings for the LDAP
            database, can be configured here.

    *   tldap.common.accountMixin:

        *   ``NUMBER_SCHEME``: What unique numbering system to use for this
            LDAP server. Allows using different uidNumber for different servers.
        *   ``UID_FIRST``: The first uidNumber to use for the first account.

    *   tldap.common.groupMixin:

        *   ``NUMBER_SCHEME``: What unique numbering system to use for this
            LDAP server. Allows using different gidNumber for different
            servers.
        *   ``GID_FIRST``: The first gidNumber to use for the first account.

    *   tldap.common.sambaAccountMixin

        *   ``SAMBA_ACCOUNT_RID_BASE``: First RID to use for SID.
        *   ``SAMBA_DOMAIN_SID``: The SID, not counting the last component, the
            RID.

    *   tldap.common.sambaGroupMixin

        *   ``SAMBA_GROUP_RID_BASE``: First RID to use for the SID.
        *   ``SAMBA_DOMAIN_SID``: The SID, not counting the last component, the
            RID.

    *   methods.shibboleth

        *   ``SHIBBOLETH_URL``: Shibboleth entity ID.
        *   ``SHIBBOLETH_SALT``: Salt to use for shibboleth shared tokens.

#.  For some real examples on how methods are used, see the `karaage
    <https://github.com/Karaage-Cluster/karaage>`_ and `django-placard
    <https://github.com/VPAC/django-placard>`_ projects.
