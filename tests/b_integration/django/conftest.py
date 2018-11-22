from django.conf import settings as djsettings
import pytest


@pytest.fixture
def settings():
    return djsettings.LDAP
