import pytest

import tldap.database
from tldap.django.models import Counters
from tldap.tests.django.database import Group


@pytest.mark.django_db(transaction=True)
def test_create(LDAP_ou):
    """ Test create LDAP object. """

    # Create the object.
    group_1 = Group({
        'cn': 'penguins1',
        'memberUid': [],
    })

    group_1 = tldap.database.insert(group_1)
    assert group_1['gidNumber'] == 10000

    group_2 = Group({
        'cn': 'penguins2',
        'memberUid': [],
    })

    group_2 = tldap.database.insert(group_2)
    assert group_2['gidNumber'] == 10001

    group_3 = Group({
        'cn': 'penguins3',
        'memberUid': [],
    })

    group_3 = tldap.database.insert(group_3)
    assert group_3['gidNumber'] == 10002


@pytest.mark.django_db(transaction=True)
def test_create_with_reset(LDAP_ou):
    """ Test create LDAP object. """

    # Create the object.
    group_1 = Group({
        'cn': 'penguins1',
        'memberUid': [],
    })

    group_1 = tldap.database.insert(group_1)
    assert group_1['gidNumber'] == 10000

    Counters.objects.all().delete()

    group_2 = Group({
        'cn': 'penguins2',
        'memberUid': [],
    })

    group_2 = tldap.database.insert(group_2)
    assert group_2['gidNumber'] == 10001

    Counters.objects.all().delete()

    group_3 = Group({
        'cn': 'penguins3',
        'memberUid': [],
    })

    group_3 = tldap.database.insert(group_3)
    assert group_3['gidNumber'] == 10002