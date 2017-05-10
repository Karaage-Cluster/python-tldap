import behave
from ldap3.core import exceptions
import pytest

from tldap.tests import schemas as test_schemas


@behave.when(u'we create a person called {username}')
def step_create_person(context, username):
    """ Test if we can create a person. """
    person_attributes = {
        'uid': username,
        'givenName': "Tux",
        'sn': "Torvalds",
        'cn': "Tux Torvalds",
        'telephoneNumber': "000",
        'mail': "tuz@example.org",
        'o': "Linux Rules",
        'userPassword': "silly",
    }
    test_schemas.person.objects.create(**person_attributes)


@behave.when(u'we modify a person called {username}')
def step_modify_person(context, username):
    """ Test if we can modify a person. """
    person = test_schemas.person.objects.get(uid=username)
    person.cn = "Super Tux"
    person.sn = "Tux"
    person.givenName = "Super Tux"
    person.save()


@behave.when(u'we delete a person called {username}')
def step_delete_person(context, username):
    """ Test if we can delete a person. """
    person = test_schemas.person.objects.get(uid=username)
    person.delete()


@behave.then(u'we should be able to search for a person')
def step_search_person(context):
    """ Test we can search. """
    list(test_schemas.person.objects.all())


@behave.then(u'we should not be able to search for a person')
def step_not_search_person(context):
    """ Test we can search. """
    with pytest.raises(exceptions.LDAPInvalidCredentialsResult):
        list(test_schemas.person.objects.all())


@behave.then(u'we should be able to get a person called {username}')
def step_get_person_success(context, username):
    context.obj = test_schemas.person.objects.get(uid=username)


@behave.then(u'we should not be able to get a person called {username}')
def step_get_person_not_found(context, username):
    with pytest.raises(test_schemas.person.DoesNotExist):
        test_schemas.person.objects.get(uid=username)


@behave.then(u'we should be able to find {count:d} persons')
def step_count_persons(context, count):
    assert count == len(test_schemas.person.objects.all())
