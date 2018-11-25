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
def settings():
    return {
        'default': {
            'ENGINE': 'tldap.backend.fake_transactions',
            'URI': os.environ['LDAP_URL'],
            'USER': os.environ['LDAP_DN'],
            'PASSWORD': os.environ['LDAP_PASSWORD'],
            'USE_TLS': False,
            'TLS_CA': None,
            'LDAP_ACCOUNT_BASE': os.environ['LDAP_ACCOUNT_BASE'],
            'LDAP_GROUP_BASE': os.environ['LDAP_GROUP_BASE'],
            'NUMBER_SCHEME': 'default',
        }
    }


@pytest.fixture
def ldap(settings):
    tldap.backend.setup(settings)

    connection = tldap.backend.connections['default']
    yield connection

    delete(connection, f"uid=tux,{os.environ['LDAP_ACCOUNT_BASE']}")
    delete(connection, f"uid=tuz,{os.environ['LDAP_ACCOUNT_BASE']}")
    delete(connection, f"uid=tux,{os.environ['LDAP_GROUP_BASE']}")

    delete(connection, f"cn=tux,{os.environ['LDAP_GROUP_BASE']}")
    delete(connection, f"cn=tuz,{os.environ['LDAP_GROUP_BASE']}")
    delete(connection, f"cn=tux,{os.environ['LDAP_ACCOUNT_BASE']}")

    delete(connection, f"uid=tux1,{os.environ['LDAP_ACCOUNT_BASE']}")
    delete(connection, f"uid=tux2,{os.environ['LDAP_ACCOUNT_BASE']}")
    delete(connection, f"uid=tux3,{os.environ['LDAP_ACCOUNT_BASE']}")

    delete(connection, f"cn=penguins1,{os.environ['LDAP_GROUP_BASE']}")
    delete(connection, f"cn=penguins2,{os.environ['LDAP_GROUP_BASE']}")
    delete(connection, f"cn=penguins3,{os.environ['LDAP_GROUP_BASE']}")


@pytest.fixture
def context():
    return {}


@when('we enter a transaction')
def step_start_transaction(ldap):
    transaction.enter_transaction_management()


@when('we commit the transaction')
def step_commit_transaction(ldap):
    transaction.commit()
    transaction.leave_transaction_management()


@when('we rollback the transaction')
def step_rollback_transaction(ldap):
    transaction.rollback()
    transaction.leave_transaction_management()


@then(parsers.cfparse(
    'we should be able confirm the {attribute} attribute is {value}'))
def step_confirm_attribute(context, attribute, value):
    actual_value = context['obj'].get_as_single(attribute)
    assert str(actual_value) == value, attribute
