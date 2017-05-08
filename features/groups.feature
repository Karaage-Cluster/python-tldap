Feature: Testing group functions

  Scenario: Test create group
      when we enter a transaction
      and we create a group called tux
      and we commit the transaction
      then we should be able to get a group called tux
      and we should be able confirm the gidNumber attribute is 10
      and we should be able to find 1 groups

  Scenario: Test create group with rollback
      when we enter a transaction
      and we create a group called tux
      and we rollback the transaction
      then we should not be able to get a group called tux
      and we should be able to find 0 groups

  Scenario: Test create 2 groups
      when we enter a transaction
      and we create a group called tux
      and we create a group called tuz
      and we commit the transaction
      then we should be able to get a group called tux
      and we should be able to get a group called tuz
      and we should be able to find 2 groups

  Scenario: Test modify group
      when we create a group called tux
      and we enter a transaction
      and we modify a group called tux
      and we commit the transaction
      then we should be able to get a group called tux
      and we should be able confirm the gidNumber attribute is 11

  Scenario: Test modify group with rollback
      when we create a group called tux
      and we enter a transaction
      and we modify a group called tux
      and we rollback the transaction
      then we should be able to get a group called tux
      and we should be able confirm the gidNumber attribute is 10

  Scenario: Test create 2 groups with rollback
      when we enter a transaction
      and we create a group called tux
      and we create a group called tuz
      and we rollback the transaction
      then we should not be able to get a group called tux
      and we should not be able to get a group called tuz
      and we should be able to find 0 groups

  Scenario: Test delete group
      when we create a group called tux
      and we enter a transaction
      and we delete a group called tux
      and we commit the transaction
      then we should not be able to get a group called tux
      and we should be able to find 0 groups

  Scenario: Test delete group with rollback
      when we create a group called tux
      and we enter a transaction
      and we delete a group called tux
      and we rollback the transaction
      then we should be able to get a group called tux
      and we should be able to find 1 groups
