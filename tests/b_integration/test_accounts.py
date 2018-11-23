import os

from ldap3.core import exceptions
import pytest
from pytest_bdd import scenarios, when, then, parsers

import tldap.database
from tldap import Q
import tldap.backend.base
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
    changes = tldap.database.get_changes(account, {
        'sn': "Tux",
        'givenName': "Super",
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


def test_lock_account(account, ldap: tldap.backend.base.LdapBase):
    # Check account is unlocked.
    assert account['locked'] is False
    assert account['loginShell'] == "/bin/bash"
    assert ldap.check_password(account['dn'], 'silly') is True

    # Lock account.
    changes = tldap.database.get_changes(account, {'locked': True})
    account = tldap.database.save(changes)

    # Check account is locked.
    assert account['locked'] is True
    assert account['loginShell'] == "/locked/bin/bash"

    account = tldap.database.get_one(Account, Q(uid='tux'))

    assert account['locked'] is True
    assert account['loginShell'] == "/locked/bin/bash"

    assert ldap.check_password(account['dn'], 'silly') is False

    # Change the login shell
    changes = tldap.database.get_changes(account, {'loginShell': '/bin/zsh'})
    account = tldap.database.save(changes)

    # Check the account is still locked.
    assert account['locked'] is True
    assert account['loginShell'] == "/locked/bin/zsh"

    account = tldap.database.get_one(Account, Q(uid='tux'))

    assert account['locked'] == True
    assert account['loginShell'] == "/locked/bin/zsh"

    assert ldap.check_password(account['dn'], 'silly') is False

    # Unlock the account.
    changes = tldap.database.get_changes(account, {'locked': False})
    account = tldap.database.save(changes)

    # Check the account is now unlocked.
    assert account['locked'] is False
    assert account['loginShell'] == "/bin/zsh"

    account = tldap.database.get_one(Account, Q(uid='tux'))

    assert account['locked'] is False
    assert account['loginShell'] == "/bin/zsh"

    assert ldap.check_password(account['dn'], 'silly') is True


@pytest.mark.skipif(os.environ['LDAP_TYPE'] != 'openldap', reason="Require OpenLDAP")
def test_lock_account_openldap(account, ldap: tldap.backend.base.LdapBase):
    # Check account is unlocked.
    assert account['locked'] is False
    assert account['pwdAccountLockedTime'] is None
    assert ldap.check_password(account['dn'], 'silly') is True

    # Lock account.
    changes = tldap.database.get_changes(account, {'locked': True})
    account = tldap.database.save(changes)

    # Check account is locked.
    assert account['locked'] is True
    assert account['pwdAccountLockedTime'] == "000001010000Z"

    account = tldap.database.get_one(Account, Q(uid='tux'))

    assert account['locked'] is True
    assert account['pwdAccountLockedTime'] == "000001010000Z"

    assert ldap.check_password(account['dn'], 'silly') is False

    # Unlock the account.
    changes = tldap.database.get_changes(account, {'locked': False})
    account = tldap.database.save(changes)

    # Check the account is now unlocked.
    assert account['locked'] is False
    assert account['pwdAccountLockedTime'] is None

    account = tldap.database.get_one(Account, Q(uid='tux'))

    assert account['locked'] is False
    assert account['pwdAccountLockedTime'] is None

    assert ldap.check_password(account['dn'], 'silly') is True
