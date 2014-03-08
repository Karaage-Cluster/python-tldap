History
=======

Ideas that seemed like a good idea at the time that have been adandoned. These
are documented here to avoid accidentally reimplementing bad ideas without
consideration at to why they were discarded.


*   Process actions immediately.

    Previously, would delay processing actions until commit() called.

    This requires caching the attributes, and simulating the actions in
    cache. Unfortunately this is very difficult to get right, particular
    as certain actions can have different side effects (e.g. alter other
    attributes) depending on the server.

    Also we run into the problem that any errors during the commit()
    phase may happen too late to abort changes to other databases. e.g.
    if the Django middleware is used, any errors generated in the middleware
    will not affect the other middleware transaction layers for other
    databases, and they will continue to commit all results (regardless
    of order of invocation).

    So we process the results immediately. This means rollback is
    more likely to be required when something doesn't work, which could
    introduce problems if this failes. However these changes, I believe
    will result in an overall simpler and more robust design.

    commit: a6180486dc788c6ba81dcbff1e6c9a0bbbc481f3

*   Remove caching in backend. No longer needed now we process actions
    immediately.

    commit: 21e357bfc612c1fd1ef1ca599a5dbb39a94fac1e

*   Remove using= parameter from object methods.

    Initially this was copied from Django db models.

    This means if we load object from LDAP server we have to save it to that
    same LDAP server.

    In a practical sense, this was the case anyway.

    Trying to make things too generic just over complicates everything.

    This also means that the dn for an object will not change, unless rename
    is called. To try and do otherwise is just so very very confusing. 

    As a result, a lot of complicated code that was potentially broken has now
    been simplified.

    commit: 9f79c500bc971ad7fdd3dd6e4eb45d1b187d5f03
