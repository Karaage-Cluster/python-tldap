from ldap3.core import exceptions
import pytest
from pytest_bdd import scenarios, when, then, parsers

import tldap.database
from tldap import Q
from tldap.django.models import Counters
from tldap.exceptions import ObjectDoesNotExist
from tests.database import Group

scenarios('groups.feature')


@when(parsers.cfparse('we create a group called {name}'))
def step_create_group(ldap, name):
    """ Test if we can create a group. """
    group = Group({
        'cn': name,
        'gidNumber': 10,
        'memberUid': [],
    })
    tldap.database.insert(group)


@when(parsers.cfparse('we modify a group called {name}'))
def step_modify_group(ldap, name):
    """ Test if we can modify a group. """
    group = tldap.database.get_one(Group, Q(cn=name))
    changes = tldap.database.changeset(group, {'gidNumber': 11})
    tldap.database.save(changes)
    group = tldap.database.get_one(Group, Q(cn=name))
    print("modify", group['cn'])


@when(parsers.cfparse('we rename a group called {name} to {new_name}'))
def step_rename_group(ldap, name, new_name):
    """ Test if we can rename a group. """
    group = tldap.database.get_one(Group, Q(cn=name))
    tldap.database.rename(group, cn=new_name)


@when(parsers.cfparse('we move a group called {name} to {new_dn}'))
def step_move_group(ldap, name, new_dn):
    """ Test if we can move a group. """
    group = tldap.database.get_one(Group, Q(cn=name))
    tldap.database.rename(group, new_dn)


@when(parsers.cfparse('we delete a group called {name}'))
def step_delete_group(ldap, name):
    """ Test if we can delete a group. """
    group = tldap.database.get_one(Group, Q(cn=name))
    tldap.database.delete(group)


@then('we should be able to search for a group')
def step_search_group(ldap):
    """ Test we can search. """


@then('we should not be able to search for a group')
def step_not_search_group(ldap):
    """ Test we can search. """
    with pytest.raises(exceptions.LDAPInvalidCredentialsResult):
        list(tldap.database.search(Group))


@then(parsers.cfparse('we should be able to get a group called {name}'))
def step_get_group_success(ldap, context, name):
    group = tldap.database.get_one(Group, Q(cn=name))
    context['obj'] = group
    print("get", group['cn'])


@then(parsers.cfparse('we should not be able to get a group called {name}'))
def step_get_group_not_found(ldap, name):
    with pytest.raises(ObjectDoesNotExist):
        tldap.database.get_one(Group, Q(cn=name))


@then(parsers.cfparse(
    'we should be able to get a group at dn {dn} called {name}'))
def step_get_group_dn_success(ldap, context, name, dn):
    context['obj'] = tldap.database.get_one(Group, Q(cn=name), base_dn=dn)


@then(parsers.cfparse(
    'we should not be able to get a group at dn {dn} called {name}'))
def step_get_group_dn_not_found(ldap, name, dn):
    with pytest.raises(ObjectDoesNotExist):
        tldap.database.get_one(Group, Q(cn=name), base_dn=dn)


@then(parsers.cfparse('we should be able to find {count:d} groups'))
def step_count_groups(ldap, count):
    assert count == len(list(tldap.database.search(Group)))


@pytest.mark.django_db(transaction=True)
def test_create(ldap):
    """ Test create LDAP object. """

    # Create the object.
    group_1 = Group({
        'cn': 'penguins1',
        'memberUid': [],
    })

    group_1 = tldap.database.insert(group_1)
    assert group_1['gidNumber'] == [10000]

    group_2 = Group({
        'cn': 'penguins2',
        'memberUid': [],
    })

    group_2 = tldap.database.insert(group_2)
    assert group_2['gidNumber'] == [10001]

    group_3 = Group({
        'cn': 'penguins3',
        'memberUid': [],
    })

    group_3 = tldap.database.insert(group_3)
    assert group_3['gidNumber'] == [10002]


@pytest.mark.django_db(transaction=True)
def test_create_with_reset(ldap):
    """ Test create LDAP object. """

    # Create the object.
    group_1 = Group({
        'cn': 'penguins1',
        'memberUid': [],
    })

    group_1 = tldap.database.insert(group_1)
    assert group_1['gidNumber'] == [10000]

    Counters.objects.all().delete()

    group_2 = Group({
        'cn': 'penguins2',
        'memberUid': [],
    })

    group_2 = tldap.database.insert(group_2)
    assert group_2['gidNumber'] == [10001]

    Counters.objects.all().delete()

    group_3 = Group({
        'cn': 'penguins3',
        'memberUid': [],
    })

    group_3 = tldap.database.insert(group_3)
    assert group_3['gidNumber'] == [10002]