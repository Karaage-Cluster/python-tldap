Feature: Testing person functions

  Scenario: Create person
      When we enter a transaction
      And we create a person called tux
      And we commit the transaction
      Then we should be able to get a person called tux
      And we should be able confirm the cn attribute is Tux Torvalds
      And we should be able to find 1 persons

  Scenario: Create person with rollback
      When we enter a transaction
      And we create a person called tux
      And we rollback the transaction
      Then we should not be able to get a person called tux
      And we should be able to find 0 persons

  Scenario: Create 2 persons
      When we enter a transaction
      And we create a person called tux
      And we create a person called tuz
      And we commit the transaction
      Then we should be able to get a person called tux
      And we should be able to get a person called tuz
      And we should be able to find 2 persons

  Scenario: Modify person
      When we create a person called tux
      And we enter a transaction
      And we modify a person called tux
      And we commit the transaction
      Then we should be able to get a person called tux
      And we should be able confirm the cn attribute is Super Tux

  Scenario: Modify person with rollback
      When we create a person called tux
      And we enter a transaction
      And we modify a person called tux
      And we rollback the transaction
      Then we should be able to get a person called tux
      And we should be able confirm the cn attribute is Tux Torvalds

  Scenario: Create 2 persons with rollback
      When we enter a transaction
      And we create a person called tux
      And we create a person called tuz
      And we rollback the transaction
      Then we should not be able to get a person called tux
      And we should not be able to get a person called tuz
      And we should be able to find 0 persons

  Scenario: Delete person
      When we create a person called tux
      And we enter a transaction
      And we delete a person called tux
      And we commit the transaction
      Then we should not be able to get a person called tux
      And we should be able to find 0 persons

  Scenario: Delete person with rollback
      When we create a person called tux
      And we enter a transaction
      And we delete a person called tux
      And we rollback the transaction
      Then we should be able to get a person called tux
      And we should be able to find 1 persons

  Scenario: Rename person
      When we create a person called tux
      And we enter a transaction
      And we rename a person called tux to tuz
      And we commit the transaction
      Then we should not be able to get a person called tux
      Then we should be able to get a person called tuz
      And we should be able to find 1 persons

  Scenario: Rename person with rollback
      When we create a person called tux
      And we enter a transaction
      And we rename a person called tux to tuz
      And we rollback the transaction
      Then we should be able to get a person called tux
      Then we should not be able to get a person called tuz
      And we should be able to find 1 persons

  Scenario: Move person
      When we create a person called tux
      And we enter a transaction
      And we move a person called tux to ou=Groups,dc=python-ldap,dc=org
      And we commit the transaction
      Then we should not be able to get a person called tux
      And we should be able to get a person at dn ou=Groups,dc=python-ldap,dc=org called tux
      And we should be able to find 0 persons

  Scenario: Move person with rollback
      When we create a person called tux
      And we enter a transaction
      And we move a person called tux to ou=Groups,dc=python-ldap,dc=org
      And we rollback the transaction
      Then we should be able to get a person called tux
      And we should not be able to get a person at dn ou=Groups,dc=python-ldap,dc=org called tux
      And we should be able to find 1 persons
