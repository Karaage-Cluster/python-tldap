from ldap3.core import exceptions
import pytest
from pytest_bdd import scenarios, when, then, parsers

from tldap.tests import schemas as test_schemas

scenarios('groups.feature')


@when(parsers.cfparse('we create a group called {name}'))
def step_create_group(LDAP_ou, name):
    """ Test if we can create a group. """
    group_attributes = {
        'cn': name,
        'gidNumber': 10,
        'memberUid': [],
    }
    test_schemas.group.objects.create(**group_attributes)


@when(parsers.cfparse('we modify a group called {name}'))
def step_modify_group(LDAP_ou, name):
    """ Test if we can modify a group. """
    group = test_schemas.group.objects.get(cn=name)
    group.gidNumber = 11
    group.save()
    group = test_schemas.group.objects.get(cn=name)
    print("modify", group.cn)


@when(parsers.cfparse('we rename a group called {name} to {new_name}'))
def step_rename_group(LDAP_ou, name, new_name):
    """ Test if we can rename a group. """
    group = test_schemas.group.objects.get(cn=name)
    group.rename(cn=new_name)


@when(parsers.cfparse('we move a group called {name} to {new_dn}'))
def step_move_group(LDAP_ou, name, new_dn):
    """ Test if we can move a group. """
    group = test_schemas.group.objects.get(cn=name)
    group.rename(new_dn)


@when(parsers.cfparse('we delete a group called {name}'))
def step_delete_group(LDAP_ou, name):
    """ Test if we can delete a group. """
    group = test_schemas.group.objects.get(cn=name)
    group.delete()


@then('we should be able to search for a group')
def step_search_group(LDAP_ou):
    """ Test we can search. """


@then('we should not be able to search for a group')
def step_not_search_group(LDAP_ou):
    """ Test we can search. """
    with pytest.raises(exceptions.LDAPInvalidCredentialsResult):
        list(test_schemas.group.objects.all())


@then(parsers.cfparse('we should be able to get a group called {name}'))
def step_get_group_success(LDAP_ou, context, name):
    group = test_schemas.group.objects.get(cn=name)
    context['obj'] = group
    print("get", group.cn)


@then(parsers.cfparse('we should not be able to get a group called {name}'))
def step_get_group_not_found(LDAP_ou, name):
    with pytest.raises(test_schemas.group.DoesNotExist):
        test_schemas.group.objects.get(cn=name)


@then(parsers.cfparse(
    'we should be able to get a group at dn {dn} called {name}'))
def step_get_group_dn_success(LDAP_ou, context, name, dn):
    context['obj'] = test_schemas.group.objects.base_dn(dn).get(cn=name)


@then(parsers.cfparse(
    'we should not be able to get a group at dn {dn} called {name}'))
def step_get_group_dn_not_found(LDAP_ou, name, dn):
    with pytest.raises(test_schemas.group.DoesNotExist):
        test_schemas.group.objects.base_dn(dn).get(cn=name)


@then(parsers.cfparse('we should be able to find {count:d} groups'))
def step_count_groups(LDAP_ou, count):
    assert count == len(test_schemas.group.objects.all())
