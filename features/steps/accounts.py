import behave
from ldap3.core import exceptions
import pytest

from tldap.tests import schemas as test_schemas


@behave.when(u'we create a account called {username}')
def step_create_account(context, username):
    """ Test if we can create a account. """
    account_attributes = {
        'uid': username,
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


@behave.when(u'we modify a account called {username}')
def step_modify_account(context, username):
    """ Test if we can modify a account. """
    account = test_schemas.account.objects.get(uid=username)
    account.cn = "Super Tux"
    account.sn = "Tux"
    account.givenName = "Super Tux"
    account.save()


@behave.when(u'we rename a account called {name} to {new_name}')
def step_rename_account(context, name, new_name):
    """ Test if we can rename a account. """
    account = test_schemas.account.objects.get(uid=name)
    account.rename(uid=new_name)


@behave.when(u'we move a account called {name} to {new_dn}')
def step_move_account(context, name, new_dn):
    """ Test if we can move a account. """
    account = test_schemas.account.objects.get(uid=name)
    account.rename(new_dn)


@behave.when(u'we delete a account called {username}')
def step_delete_account(context, username):
    """ Test if we can delete a account. """
    account = test_schemas.account.objects.get(uid=username)
    account.delete()


@behave.then(u'we should be able to search for a account')
def step_search_account(context):
    """ Test we can search. """
    list(test_schemas.account.objects.all())


@behave.then(u'we should not be able to search for a account')
def step_not_search_account(context):
    """ Test we can search. """
    with pytest.raises(exceptions.LDAPInvalidCredentialsResult):
        list(test_schemas.account.objects.all())


@behave.then(u'we should be able to get a account called {username}')
def step_get_account_success(context, username):
    context.obj = test_schemas.account.objects.get(uid=username)


@behave.then(u'we should not be able to get a account called {username}')
def step_get_account_not_found(context, username):
    with pytest.raises(test_schemas.account.DoesNotExist):
        test_schemas.account.objects.get(uid=username)


@behave.then(u'we should be able to find {count:d} accounts')
def step_count_accounts(context, count):
    assert count == len(test_schemas.account.objects.all())
