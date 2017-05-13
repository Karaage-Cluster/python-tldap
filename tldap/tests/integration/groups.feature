Feature: Testing group functions

  Scenario: Create group
      When we enter a transaction
      And we create a group called tux
      And we commit the transaction
      Then we should be able to get a group called tux
      And we should be able confirm the gidNumber attribute is 10
      And we should be able to find 1 groups

  Scenario: Create group with rollback
      When we enter a transaction
      And we create a group called tux
      And we rollback the transaction
      Then we should not be able to get a group called tux
      And we should be able to find 0 groups

  Scenario: Create 2 groups
      When we enter a transaction
      And we create a group called tux
      And we create a group called tuz
      And we commit the transaction
      Then we should be able to get a group called tux
      And we should be able to get a group called tuz
      And we should be able to find 2 groups

  Scenario: Modify group
      When we create a group called tux
      And we enter a transaction
      And we modify a group called tux
      And we commit the transaction
      Then we should be able to get a group called tux
      And we should be able confirm the gidNumber attribute is 11

  Scenario: Modify group with rollback
      When we create a group called tux
      And we enter a transaction
      And we modify a group called tux
      And we rollback the transaction
      Then we should be able to get a group called tux
      And we should be able confirm the gidNumber attribute is 10

  Scenario: Create 2 groups with rollback
      When we enter a transaction
      And we create a group called tux
      And we create a group called tuz
      And we rollback the transaction
      Then we should not be able to get a group called tux
      And we should not be able to get a group called tuz
      And we should be able to find 0 groups

  Scenario: Delete group
      When we create a group called tux
      And we enter a transaction
      And we delete a group called tux
      And we commit the transaction
      Then we should not be able to get a group called tux
      And we should be able to find 0 groups

  Scenario: Delete group with rollback
      When we create a group called tux
      And we enter a transaction
      And we delete a group called tux
      And we rollback the transaction
      Then we should be able to get a group called tux
      And we should be able to find 1 groups

  Scenario: Rename group
      When we create a group called tux
      And we enter a transaction
      And we rename a group called tux to tuz
      And we commit the transaction
      Then we should not be able to get a group called tux
      Then we should be able to get a group called tuz
      And we should be able to find 1 groups

  Scenario: Rename group with rollback
      When we create a group called tux
      And we enter a transaction
      And we rename a group called tux to tuz
      And we rollback the transaction
      Then we should be able to get a group called tux
      Then we should not be able to get a group called tuz
      And we should be able to find 1 groups

  Scenario: Move group
      When we create a group called tux
      And we enter a transaction
      And we move a group called tux to ou=People,dc=python-ldap,dc=org
      And we commit the transaction
      Then we should not be able to get a group called tux
      And we should be able to get a group at dn ou=People,dc=python-ldap,dc=org called tux
      And we should be able to find 0 groups

  Scenario: Move group with rollback
      When we create a group called tux
      And we enter a transaction
      And we move a group called tux to ou=People,dc=python-ldap,dc=org
      And we rollback the transaction
      Then we should be able to get a group called tux
      And we should not be able to get a group at dn ou=People,dc=python-ldap,dc=org called tux
      And we should be able to find 1 groups
