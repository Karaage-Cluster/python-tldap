Future work
===========

*   Some servers, e.g. Active Directory, support transactions properly in the
    server. Need to support these transactions natively.

*   The Active Directory primary group field type has never been implemented
    correctly for the entire set of operations. This is due to the complicated
    nature of some of the side effects when dealing with this field.

*   Initial tests seem to indicate that the account locking/unlocking code for
    Directory Server 389 does not lock the account. Need to fix this.

*   Remove dependancy on Django? There are only a limited number of places that
    reference Django:

    #.  tldap/__init__.py: django settings
    #.  tldap/methods/models.py: django db model
    #.  tldap/query_utils.py: django.utils.tree.Node
    #.  tldap/manager.py: django.utils.importlib
    #.  tldap/options.py: django.utils.translation
