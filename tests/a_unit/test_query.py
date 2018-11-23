import tldap
import tldap.query
import tests.database


def test_filter_normal():
    """ Test filter. """
    ldap_filter = tldap.query.get_filter(
        tldap.Q(uid='tux'),
        tests.database.Account.get_fields(),
        "uid"
    )
    assert ldap_filter == b"(uid=tux)"


def test_filter_backslash():
    """ Test filter with backslash. """
    ldap_filter = tldap.query.get_filter(
        tldap.Q(uid='t\\ux'),
        tests.database.Account.get_fields(),
        "uid"
    )
    assert ldap_filter == b"(uid=t\\5cux)"


def test_filter_negated():
    """ Test filter with negated value. """
    ldap_filter = tldap.query.get_filter(
        ~tldap.Q(uid='tux'),
        tests.database.Account.get_fields(),
        "uid"
    )
    assert ldap_filter == b"(!(uid=tux))"


def test_filter_or_2():
    """ Test filter with OR condition. """
    ldap_filter = tldap.query.get_filter(
        tldap.Q(uid='tux') | tldap.Q(uid='tuz'),
        tests.database.Account.get_fields(),
        "uid"
    )
    assert ldap_filter == b"(|(uid=tux)(uid=tuz))"


def test_filter_or_3():
    """ Test filter with OR condition """
    ldap_filter = tldap.query.get_filter(
        tldap.Q() | tldap.Q(uid='tux') | tldap.Q(uid='tuz'),
        tests.database.Account.get_fields(),
        "uid"
    )
    assert ldap_filter == b"(|(uid=tux)(uid=tuz))"


def test_filter_and():
    """ Test filter with AND condition. """
    ldap_filter = tldap.query.get_filter(
        tldap.Q() & tldap.Q(uid='tux') & tldap.Q(uid='tuz'),
        tests.database.Account.get_fields(),
        "uid"
    )
    assert ldap_filter == b"(&(uid=tux)(uid=tuz))"


def test_filter_and_or():
    """ Test filter with AND and OR condition. """
    ldap_filter = tldap.query.get_filter(
        tldap.Q(uid='tux') & (tldap.Q(uid='tuz') | tldap.Q(uid='meow')),
        tests.database.Account.get_fields(),
        "uid"
    )
    assert ldap_filter == b"(&(uid=tux)(|(uid=tuz)(uid=meow)))"
