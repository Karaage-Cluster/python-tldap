import behave
from ldap3.core import exceptions
import pytest

from tldap.tests import schemas as test_schemas


@behave.when(u'we create a group called {name}')
def step_create_group(context, name):
    """ Test if we can create a group. """
    group_attributes = {
        'cn': name,
        'gidNumber': 10,
        'memberUid': [],
    }
    test_schemas.group.objects.create(**group_attributes)


@behave.when(u'we modify a group called {name}')
def step_modify_group(context, name):
    """ Test if we can modify a group. """
    group = test_schemas.group.objects.get(cn=name)
    group.gidNumber = 11
    group.save()


@behave.when(u'we delete a group called {name}')
def step_delete_group(context, name):
    """ Test if we can delete a group. """
    group = test_schemas.group.objects.get(cn=name)
    group.delete()


@behave.then(u'we should be able to search for a group')
def step_search_group(context):
    """ Test we can search. """
    list(test_schemas.group.objects.all())


@behave.then(u'we should not be able to search for a group')
def step_not_search_group(context):
    """ Test we can search. """
    with pytest.raises(exceptions.LDAPInvalidCredentialsResult):
        list(test_schemas.group.objects.all())


@behave.then(u'we should be able to get a group called {name}')
def step_get_group_success(context, name):
    context.obj = test_schemas.group.objects.get(cn=name)


@behave.then(u'we should not be able to get a group called {name}')
def step_get_group_not_found(context, name):
    with pytest.raises(test_schemas.group.DoesNotExist):
        test_schemas.group.objects.get(cn=name)


@behave.then(u'we should be able to find {count:d} groups')
def step_count_groups(context, count):
    assert count == len(test_schemas.group.objects.all())
