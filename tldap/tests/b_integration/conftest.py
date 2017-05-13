from ldap3.core import exceptions
import pytest
from pytest_bdd import given, when, then, parsers

import tldap
from tldap.tests import schemas as test_schemas
from tldap import transaction
import tldap.schemas
import tldap.test.slapd


@pytest.fixture
def LDAP(step_login):
    LDAP = {
        'default': {
            'ENGINE': 'tldap.backend.fake_transactions',
            'URI': 'ldap://localhost:38911/',
            'USER': step_login[0],
            'PASSWORD': step_login[1],
            'USE_TLS': False,
            'TLS_CA': None,
            'LDAP_ACCOUNT_BASE': 'ou=People, dc=python-ldap,dc=org',
            'LDAP_GROUP_BASE': 'ou=Groups, dc=python-ldap,dc=org'
        }
    }

    tldap.setup(LDAP)
    server = tldap.test.slapd.Slapd()
    server.set_port(38911)

    server.start()

    yield tldap.connection

    server.stop()


@pytest.fixture
def LDAP_ou(LDAP):
    organizationalUnit = tldap.schemas.rfc.organizationalUnit
    organizationalUnit.objects.create(
        dn="ou=People, dc=python-ldap,dc=org")
    organizationalUnit.objects.create(
        dn="ou=Groups, dc=python-ldap,dc=org")


@pytest.fixture
def DN():
    return "cn=Manager,dc=python-ldap,dc=org"


@pytest.fixture
def password():
    return "password"


@pytest.fixture
def context():
    return {}


@given(parsers.cfparse('we login as {DN} using {password}'))
def step_login(DN, password):
    """ Test if we can logon correctly with correct password. """
    return (DN, password)


@when('we enter a transaction')
def step_start_transaction(LDAP_ou):
    transaction.enter_transaction_management()


@when('we commit the transaction')
def step_commit_transaction(LDAP_ou):
    transaction.commit()
    transaction.leave_transaction_management()


@when('we rollback the transaction')
def step_rollback_transaction(LDAP_ou):
    transaction.rollback()
    transaction.leave_transaction_management()


@then('we should be able to search')
def step_search(LDAP_ou):
    """ Test we can search. """
    list(test_schemas.person.objects.all())


@then('we should not be able to search')
def step_not_search(LDAP):
    """ Test we can search. """
    with pytest.raises(exceptions.LDAPInvalidCredentialsResult):
        list(test_schemas.person.objects.all())


@then(parsers.cfparse(
    'we should be able confirm the {attribute} attribute is {value}'))
def step_confirm_attribute(context, attribute, value):
    actual_value = getattr(context['obj'], attribute)
    assert str(actual_value) == value
    pass
