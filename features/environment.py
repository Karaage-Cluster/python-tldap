import tldap
import tldap.test.slapd
from features.steps.utils import do_config


def before_scenario(context, scenario):
    context.server = tldap.test.slapd.Slapd()
    context.server.set_port(38911)
    context.server.start()
    do_config('cn=Manager,dc=python-ldap,dc=org', 'password')

    organizationalUnit = tldap.schemas.rfc.organizationalUnit
    organizationalUnit.objects.create(
        dn="ou=People, dc=python-ldap,dc=org")
    organizationalUnit.objects.create(
        dn="ou=Groups, dc=python-ldap,dc=org")


def after_scenario(context, scenario):
    context.server.stop()
