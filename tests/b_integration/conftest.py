import os

from ldap3.core import exceptions
import pytest
from pytest_bdd import given, when, then, parsers

import tldap
from tldap import transaction
import tldap.backend
import tldap.database


def delete(connection, dn):
    try:
        connection.delete(dn)
    except exceptions.LDAPNoSuchObjectResult:
        pass


@pytest.fixture
def LDAP():
    LDAP = {
        'default': {
            'ENGINE': 'tldap.backend.fake_transactions',
            'URI': os.environ['LDAP_URL'],
            'USER': os.environ['LDAP_DN'],
            'PASSWORD': os.environ['LDAP_PASSWORD'],
            'USE_TLS': False,
            'TLS_CA': None,
            'LDAP_ACCOUNT_BASE': os.environ['LDAP_ACCOUNT_BASE'],
            'LDAP_GROUP_BASE': os.environ['LDAP_GROUP_BASE'],
        }
    }

    tldap.backend.setup(LDAP)

    connection = tldap.backend.connections['default']
    yield connection

    delete(connection, f"uid=tux,{os.environ['LDAP_ACCOUNT_BASE']}")
    delete(connection, f"uid=tuz,{os.environ['LDAP_ACCOUNT_BASE']}")
    delete(connection, f"uid=tux,{os.environ['LDAP_GROUP_BASE']}")
    delete(connection, f"cn=tux,{os.environ['LDAP_GROUP_BASE']}")
    delete(connection, f"cn=tuz,{os.environ['LDAP_GROUP_BASE']}")
    delete(connection, f"cn=tux,{os.environ['LDAP_ACCOUNT_BASE']}")


@pytest.fixture
def LDAP_ou(LDAP):
    pass


@pytest.fixture
def context():
    return {}


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


@then(parsers.cfparse(
    'we should be able confirm the {attribute} attribute is {value}'))
def step_confirm_attribute(context, attribute, value):
    actual_value = context['obj'][attribute]
    assert str(actual_value) == value, attribute
