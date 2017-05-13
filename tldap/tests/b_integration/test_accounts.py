from ldap3.core import exceptions
import pytest
from pytest_bdd import scenarios, when, then, parsers

from tldap.tests import schemas as test_schemas

scenarios('accounts.feature')


@when(parsers.cfparse('we create a account called {name}'))
def step_create_account(LDAP_ou, name):
    """ Test if we can create a account. """
    account_attributes = {
        'uid': name,
        'givenName': "Tux",
        'sn': "Torvalds",
        'cn': "Tux Torvalds",
        'telephoneNumber': "000",
        'mail': "tuz@example.org",
        'o': "Linux Rules",
        'userPassword': "silly",
        'homeDirectory': "/home/tux",
        'gidNumber': 10,
    }
    test_schemas.account.objects.create(**account_attributes)


@when(parsers.cfparse('we modify a account called {name}'))
def step_modify_account(LDAP_ou, name):
    """ Test if we can modify a account. """
    account = test_schemas.account.objects.get(uid=name)
    account.cn = "Super Tux"
    account.sn = "Tux"
    account.givenName = "Super Tux"
    account.save()
    account = test_schemas.account.objects.get(uid=name)
    print("modify", account.cn)


@when(parsers.cfparse('we rename a account called {name} to {new_name}'))
def step_rename_account(LDAP_ou, name, new_name):
    """ Test if we can rename a account. """
    account = test_schemas.account.objects.get(uid=name)
    account.rename(uid=new_name)


@when(parsers.cfparse('we move a account called {name} to {new_dn}'))
def step_move_account(LDAP_ou, name, new_dn):
    """ Test if we can move a account. """
    account = test_schemas.account.objects.get(uid=name)
    account.rename(new_dn)


@when(parsers.cfparse('we delete a account called {name}'))
def step_delete_account(LDAP_ou, name):
    """ Test if we can delete a account. """
    account = test_schemas.account.objects.get(uid=name)
    account.delete()


@then('we should be able to search for a account')
def step_search_account(LDAP_ou):
    """ Test we can search. """


@then('we should not be able to search for a account')
def step_not_search_account(LDAP_ou):
    """ Test we can search. """
    with pytest.raises(exceptions.LDAPInvalidCredentialsResult):
        list(test_schemas.account.objects.all())


@then(parsers.cfparse('we should be able to get a account called {name}'))
def step_get_account_success(LDAP_ou, context, name):
    account = test_schemas.account.objects.get(uid=name)
    context['obj'] = account
    print("get", account.cn)


@then(parsers.cfparse('we should not be able to get a account called {name}'))
def step_get_account_not_found(LDAP_ou, name):
    with pytest.raises(test_schemas.account.DoesNotExist):
        test_schemas.account.objects.get(uid=name)


@then(parsers.cfparse(
    'we should be able to get a account at dn {dn} called {name}'))
def step_get_account_dn_success(LDAP_ou, context, name, dn):
    context['obj'] = test_schemas.account.objects.base_dn(dn).get(uid=name)


@then(parsers.cfparse(
    'we should not be able to get a account at dn {dn} called {name}'))
def step_get_account_dn_not_found(LDAP_ou, name, dn):
    with pytest.raises(test_schemas.account.DoesNotExist):
        test_schemas.account.objects.base_dn(dn).get(uid=name)


@then(parsers.cfparse('we should be able to find {count:d} accounts'))
def step_count_accounts(LDAP_ou, count):
    assert count == len(test_schemas.account.objects.all())
