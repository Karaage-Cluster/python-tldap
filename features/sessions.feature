Feature: Testing Session Functions

  Scenario: Test login
      Given we login as cn=Manager,dc=python-ldap,dc=org using password
      then we should be able to search for a person

  Scenario: Test bad login
      Given we login as cn=Manager,dc=python-ldap,dc=org using wrong_password
      then we should not be able to search for a person
