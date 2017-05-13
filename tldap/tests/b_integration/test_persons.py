from ldap3.core import exceptions
import pytest
from pytest_bdd import scenarios, when, then, parsers

from tldap.tests import schemas as test_schemas

scenarios('persons.feature')


@when(parsers.cfparse('we create a person called {name}'))
def step_create_person(LDAP_ou, name):
    """ Test if we can create a person. """
    person_attributes = {
        'uid': name,
        'givenName': "Tux",
        'sn': "Torvalds",
        'cn': "Tux Torvalds",
        'telephoneNumber': "000",
        'mail': "tuz@example.org",
        'o': "Linux Rules",
        'userPassword': "silly",
    }
    test_schemas.person.objects.create(**person_attributes)


@when(parsers.cfparse('we modify a person called {name}'))
def step_modify_person(LDAP_ou, name):
    """ Test if we can modify a person. """
    person = test_schemas.person.objects.get(uid=name)
    person.cn = "Super Tux"
    person.sn = "Tux"
    person.givenName = "Super Tux"
    person.save()
    person = test_schemas.person.objects.get(uid=name)
    print("modify", person.cn)


@when(parsers.cfparse('we rename a person called {name} to {new_name}'))
def step_rename_person(LDAP_ou, name, new_name):
    """ Test if we can rename a person. """
    person = test_schemas.person.objects.get(uid=name)
    person.rename(uid=new_name)


@when(parsers.cfparse('we move a person called {name} to {new_dn}'))
def step_move_person(LDAP_ou, name, new_dn):
    """ Test if we can move a person. """
    person = test_schemas.person.objects.get(uid=name)
    person.rename(new_dn)


@when(parsers.cfparse('we delete a person called {name}'))
def step_delete_person(LDAP_ou, name):
    """ Test if we can delete a person. """
    person = test_schemas.person.objects.get(uid=name)
    person.delete()


@then('we should be able to search for a person')
def step_search_person(LDAP_ou):
    """ Test we can search. """


@then('we should not be able to search for a person')
def step_not_search_person(LDAP_ou):
    """ Test we can search. """
    with pytest.raises(exceptions.LDAPInvalidCredentialsResult):
        list(test_schemas.person.objects.all())


@then(parsers.cfparse('we should be able to get a person called {name}'))
def step_get_person_success(LDAP_ou, context, name):
    person = test_schemas.person.objects.get(uid=name)
    context['obj'] = person
    print("get", person.cn)


@then(parsers.cfparse('we should not be able to get a person called {name}'))
def step_get_person_not_found(LDAP_ou, name):
    with pytest.raises(test_schemas.person.DoesNotExist):
        test_schemas.person.objects.get(uid=name)


@then(parsers.cfparse(
    'we should be able to get a person at dn {dn} called {name}'))
def step_get_person_dn_success(LDAP_ou, context, name, dn):
    context['obj'] = test_schemas.person.objects.base_dn(dn).get(uid=name)


@then(parsers.cfparse(
    'we should not be able to get a person at dn {dn} called {name}'))
def step_get_person_dn_not_found(LDAP_ou, name, dn):
    with pytest.raises(test_schemas.person.DoesNotExist):
        test_schemas.person.objects.base_dn(dn).get(uid=name)


@then(parsers.cfparse('we should be able to find {count:d} persons'))
def step_count_persons(LDAP_ou, count):
    assert count == len(test_schemas.person.objects.all())
