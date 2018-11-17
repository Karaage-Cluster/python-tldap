import pytest

import tldap.database
from tldap.django.models import Counters
from tldap.tests.django.database import Account


@pytest.mark.django_db(transaction=True)
def test_create(LDAP_ou):
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
    assert account_1['uidNumber'] == 10000

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
    assert account_2['uidNumber'] == 10001

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
    assert account_3['uidNumber'] == 10002


@pytest.mark.django_db(transaction=True)
def test_create_with_reset(LDAP_ou):
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
    assert account_1['uidNumber'] == 10000

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
    assert account_2['uidNumber'] == 10001

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
    assert account_3['uidNumber'] == 10002