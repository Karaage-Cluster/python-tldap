import os

from ldap3.core import exceptions
import pytest
from pytest_bdd import scenarios, when, then, parsers

import tldap.database
from tldap import Q
import tldap.backend.base
from tldap.django.models import Counters
from tldap.exceptions import ObjectDoesNotExist
from tests.database import Account

scenarios('accounts.feature')


@pytest.fixture
def account(ldap):
    account = Account({
        'uid': 'tux',
        'givenName': "Tux",
        'sn': "Torvalds",
        'cn': "Tux Torvalds",
        'telephoneNumber': "000",
        'mail': "tuz@example.org",
        'o': "Linux Rules",
        'userPassword': "silly",
        'homeDirectory': "/home/tux",
        'uidNumber': 10,
        'gidNumber': 10,
    })
    yield tldap.database.insert(account)


@when(parsers.cfparse('we create a account called {name}'))
def step_create_account(ldap, name):
    """ Test if we can create a account. """
    account = Account({
        'uid': name,
        'givenName': "Tux",
        'sn': "Torvalds",
        'cn': "Tux Torvalds",
        'telephoneNumber': "000",
        'mail': "tuz@example.org",
        'o': "Linux Rules",
        'userPassword': "silly",
        'homeDirectory': "/home/tux",
        'uidNumber': 10,
        'gidNumber': 10,
    })
    tldap.database.insert(account)


@when(parsers.cfparse('we modify a account called {name}'))
def step_modify_account(ldap, name):
    """ Test if we can modify a account. """
    account = tldap.database.get_one(Account, Q(uid=name))
    changes = tldap.database.changeset(account, {
        'sn': "Tux",
        'givenName': "Super",
        'cn': "Super Tux",
    })
    tldap.database.save(changes)
    account = tldap.database.get_one(Account, Q(uid=name))
    print("modify", account['cn'])


@when(parsers.cfparse('we rename a account called {name} to {new_name}'))
def step_rename_account(ldap, name, new_name):
    """ Test if we can rename a account. """
    account = tldap.database.get_one(Account, Q(uid=name))
    tldap.database.rename(account, uid=new_name)


@when(parsers.cfparse('we move a account called {name} to {new_dn}'))
def step_move_account(ldap, name, new_dn):
    """ Test if we can move a account. """
    account = tldap.database.get_one(Account, Q(uid=name))
    tldap.database.rename(account, new_dn)


@when(parsers.cfparse('we delete a account called {name}'))
def step_delete_account(ldap, name):
    """ Test if we can delete a account. """
    account = tldap.database.get_one(Account, Q(uid=name))
    tldap.database.delete(account)


@then('we should be able to search for a account')
def step_search_account(ldap):
    """ Test we can search. """
    list(tldap.database.search(Account))


@then('we should not be able to search for a account')
def step_not_search_account(ldap):
    """ Test we can search. """
    with pytest.raises(exceptions.LDAPInvalidCredentialsResult):
        list(tldap.database.search(Account))


@then(parsers.cfparse('we should be able to get a account called {name}'))
def step_get_account_success(ldap, context, name):
    account = tldap.database.get_one(Account, Q(uid=name))
    context['obj'] = account
    print("get", account['cn'])


@then(parsers.cfparse('we should not be able to get a account called {name}'))
def step_get_account_not_found(ldap, name):
    with pytest.raises(ObjectDoesNotExist):
        tldap.database.get_one(Account, Q(uid=name))


@then(parsers.cfparse(
    'we should be able to get a account at dn {dn} called {name}'))
def step_get_account_dn_success(ldap, context, name, dn):
    context['obj'] = tldap.database.get_one(Account, Q(uid=name), base_dn=dn)


@then(parsers.cfparse(
    'we should not be able to get a account at dn {dn} called {name}'))
def step_get_account_dn_not_found(ldap, name, dn):
    with pytest.raises(ObjectDoesNotExist):
        tldap.database.get_one(Account, Q(uid=name), base_dn=dn)


@then(parsers.cfparse('we should be able to find {count:d} accounts'))
def step_count_accounts(ldap, count):
    assert count == len(list(tldap.database.search(Account, None)))


@pytest.mark.django_db(transaction=True)
def test_create(ldap):
    """ Test create LDAP object. """

    # Create the object.
    account_1 = Account({
        'uid': "tux1",
        'givenName': "Tux",
        'sn': "Torvalds",
        'cn': "Tux Torvalds",
        'telephoneNumber': "000",
        'mail': "tuz@example.org",
        'o': "Linux Rules",
        'userPassword': "silly",
        'homeDirectory': "/home/tux",
        'gidNumber': 10,
    })

    account_1 = tldap.database.insert(account_1)
    assert account_1['uidNumber'] == [10000]

    account_2 = Account({
        'uid': "tux2",
        'givenName': "Tux",
        'sn': "Torvalds",
        'cn': "Tux Torvalds",
        'telephoneNumber': "000",
        'mail': "tuz@example.org",
        'o': "Linux Rules",
        'userPassword': "silly",
        'homeDirectory': "/home/tux",
        'gidNumber': 10,
    })

    account_2 = tldap.database.insert(account_2)
    assert account_2['uidNumber'] == [10001]

    account_3 = Account({
        'uid': "tux3",
        'givenName': "Tux",
        'sn': "Torvalds",
        'cn': "Tux Torvalds",
        'telephoneNumber': "000",
        'mail': "tuz@example.org",
        'o': "Linux Rules",
        'userPassword': "silly",
        'homeDirectory': "/home/tux",
        'gidNumber': 10,
    })

    account_3 = tldap.database.insert(account_3)
    assert account_3['uidNumber'] == [10002]


@pytest.mark.django_db(transaction=True)
def test_create_with_reset(ldap):
    """ Test create LDAP object. """

    # Create the object.
    account_1 = Account({
        'uid': "tux1",
        'givenName': "Tux",
        'sn': "Torvalds",
        'cn': "Tux Torvalds",
        'telephoneNumber': "000",
        'mail': "tuz@example.org",
        'o': "Linux Rules",
        'userPassword': "silly",
        'homeDirectory': "/home/tux",
        'gidNumber': 10,
    })

    account_1 = tldap.database.insert(account_1)
    assert account_1['uidNumber'] == [10000]

    Counters.objects.all().delete()

    account_2 = Account({
        'uid': "tux2",
        'givenName': "Tux",
        'sn': "Torvalds",
        'cn': "Tux Torvalds",
        'telephoneNumber': "000",
        'mail': "tuz@example.org",
        'o': "Linux Rules",
        'userPassword': "silly",
        'homeDirectory': "/home/tux",
        'gidNumber': 10,
    })

    account_2 = tldap.database.insert(account_2)
    assert account_2['uidNumber'] == [10001]

    account_3 = Account({
        'uid': "tux3",
        'givenName': "Tux",
        'sn': "Torvalds",
        'cn': "Tux Torvalds",
        'telephoneNumber': "000",
        'mail': "tuz@example.org",
        'o': "Linux Rules",
        'userPassword': "silly",
        'homeDirectory': "/home/tux",
        'gidNumber': 10,
    })

    account_3 = tldap.database.insert(account_3)
    assert account_3['uidNumber'] == [10002]


def test_lock_account(account, ldap: tldap.backend.base.LdapBase):
    # Check account is unlocked.
    assert account.get_as_single('locked') is False
    assert account.get_as_single('loginShell') == "/bin/bash"
    assert ldap.check_password(account.get_as_single('dn'), 'silly') is True

    # Lock account.
    changes = tldap.database.changeset(account, {'locked': True})
    account = tldap.database.save(changes)

    # Check account is locked.
    assert account.get_as_single('locked') is True
    assert account.get_as_single('loginShell') == "/locked/bin/bash"

    account = tldap.database.get_one(Account, Q(uid='tux'))

    assert account.get_as_single('locked') is True
    assert account.get_as_single('loginShell') == "/locked/bin/bash"

    assert ldap.check_password(account.get_as_single('dn'), 'silly') is False

    # Change the login shell
    changes = tldap.database.changeset(account, {'loginShell': '/bin/zsh'})
    account = tldap.database.save(changes)

    # Check the account is still locked.
    assert account.get_as_single('locked') is True
    assert account.get_as_single('loginShell') == "/locked/bin/zsh"

    account = tldap.database.get_one(Account, Q(uid='tux'))

    assert account.get_as_single('locked') == True
    assert account.get_as_single('loginShell') == "/locked/bin/zsh"

    assert ldap.check_password(account.get_as_single('dn'), 'silly') is False

    # Unlock the account.
    changes = tldap.database.changeset(account, {'locked': False})
    account = tldap.database.save(changes)

    # Check the account is now unlocked.
    assert account.get_as_single('locked') is False
    assert account.get_as_single('loginShell') == "/bin/zsh"

    account = tldap.database.get_one(Account, Q(uid='tux'))

    assert account.get_as_single('locked') is False
    assert account.get_as_single('loginShell') == "/bin/zsh"

    assert ldap.check_password(account.get_as_single('dn'), 'silly') is True


@pytest.mark.skipif(os.environ['LDAP_TYPE'] != 'openldap', reason="Require OpenLDAP")
def test_lock_account_openldap(account, ldap: tldap.backend.base.LdapBase):
    # Check account is unlocked.
    assert account.get_as_single('locked') is False
    assert account.get_as_list('pwdAccountLockedTime') == []
    assert ldap.check_password(account.get_as_single('dn'), 'silly') is True

    # Lock account.
    changes = tldap.database.changeset(account, {'locked': True})
    account = tldap.database.save(changes)

    # Check account is locked.
    assert account.get_as_single('locked') is True
    assert account.get_as_list('pwdAccountLockedTime') == ["000001010000Z"]

    account = tldap.database.get_one(Account, Q(uid='tux'))

    assert account.get_as_single('locked') is True
    assert account.get_as_list('pwdAccountLockedTime') == ["000001010000Z"]

    assert ldap.check_password(account.get_as_single('dn'), 'silly') is False

    # Unlock the account.
    changes = tldap.database.changeset(account, {'locked': False})
    account = tldap.database.save(changes)

    # Check the account is now unlocked.
    assert account.get_as_single('locked') is False
    assert account.get_as_list('pwdAccountLockedTime') == []

    account = tldap.database.get_one(Account, Q(uid='tux'))

    assert account.get_as_single('locked') is False
    assert account.get_as_list('pwdAccountLockedTime') == []

    assert ldap.check_password(account.get_as_single('dn'), 'silly') is True
