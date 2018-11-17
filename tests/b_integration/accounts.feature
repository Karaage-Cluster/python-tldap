Feature: Testing account functions

  Scenario: Create account
      When we enter a transaction
      And we create a account called tux
      And we commit the transaction
      Then we should be able to get a account called tux
      And we should be able confirm the cn attribute is Tux Torvalds
      And we should be able to find 1 accounts

  Scenario: Create account with rollback
      When we enter a transaction
      And we create a account called tux
      And we rollback the transaction
      Then we should not be able to get a account called tux
      And we should be able to find 0 accounts

  Scenario: Create 2 accounts
      When we enter a transaction
      And we create a account called tux
      And we create a account called tuz
      And we commit the transaction
      Then we should be able to get a account called tux
      And we should be able to get a account called tuz
      And we should be able to find 2 accounts

  Scenario: Modify account
      When we create a account called tux
      And we enter a transaction
      And we modify a account called tux
      And we commit the transaction
      Then we should be able to get a account called tux
      And we should be able confirm the cn attribute is Super Tux

  Scenario: Modify account with rollback
      When we create a account called tux
      And we enter a transaction
      And we modify a account called tux
      And we rollback the transaction
      Then we should be able to get a account called tux
      And we should be able confirm the cn attribute is Tux Torvalds

  Scenario: Create 2 accounts with rollback
      When we enter a transaction
      And we create a account called tux
      And we create a account called tuz
      And we rollback the transaction
      Then we should not be able to get a account called tux
      And we should not be able to get a account called tuz
      And we should be able to find 0 accounts

  Scenario: Delete account
      When we create a account called tux
      And we enter a transaction
      And we delete a account called tux
      And we commit the transaction
      Then we should not be able to get a account called tux
      And we should be able to find 0 accounts

  Scenario: Delete account with rollback
      When we create a account called tux
      And we enter a transaction
      And we delete a account called tux
      And we rollback the transaction
      Then we should be able to get a account called tux
      And we should be able to find 1 accounts

  Scenario: Rename account
      When we create a account called tux
      And we enter a transaction
      And we rename a account called tux to tuz
      And we commit the transaction
      Then we should not be able to get a account called tux
      Then we should be able to get a account called tuz
      And we should be able to find 1 accounts

  Scenario: Rename account with rollback
      When we create a account called tux
      And we enter a transaction
      And we rename a account called tux to tuz
      And we rollback the transaction
      Then we should be able to get a account called tux
      Then we should not be able to get a account called tuz
      And we should be able to find 1 accounts

  Scenario: Move account
      When we create a account called tux
      And we enter a transaction
      And we move a account called tux to ou=Groups,dc=python-ldap,dc=org
      And we commit the transaction
      Then we should not be able to get a account called tux
      And we should be able to get a account at dn ou=Groups,dc=python-ldap,dc=org called tux
      And we should be able to find 0 accounts

  Scenario: Move account with rollback
      When we create a account called tux
      And we enter a transaction
      And we move a account called tux to ou=Groups,dc=python-ldap,dc=org
      And we rollback the transaction
      Then we should be able to get a account called tux
      And we should not be able to get a account at dn ou=Groups,dc=python-ldap,dc=org called tux
      And we should be able to find 1 accounts
