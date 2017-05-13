Feature: Testing Session Functions

  Scenario: Test login
      Given we login as cn=Manager,dc=python-ldap,dc=org using password
      Then we should be able to search

  Scenario: Test bad login
      Given we login as cn=Manager,dc=python-ldap,dc=org using wrong_password
      Then we should not be able to search
