Feature: Testing person functions

  Scenario: Test create person
      when we enter a transaction
      and we create a person called tux
      and we commit the transaction
      then we should be able to get a person called tux
      and we should be able confirm the cn attribute is Tux Torvalds
      and we should be able to find 1 persons

  Scenario: Test create person with rollback
      when we enter a transaction
      and we create a person called tux
      and we rollback the transaction
      then we should not be able to get a person called tux
      and we should be able to find 0 persons

  Scenario: Test create 2 persons
      when we enter a transaction
      and we create a person called tux
      and we create a person called tuz
      and we commit the transaction
      then we should be able to get a person called tux
      and we should be able to get a person called tuz
      and we should be able to find 2 persons

  Scenario: Test modify person
      when we create a person called tux
      and we enter a transaction
      and we modify a person called tux
      and we commit the transaction
      then we should be able to get a person called tux
      and we should be able confirm the cn attribute is Super Tux

  Scenario: Test modify person with rollback
      when we create a person called tux
      and we enter a transaction
      and we modify a person called tux
      and we rollback the transaction
      then we should be able to get a person called tux
      and we should be able confirm the cn attribute is Tux Torvalds

  Scenario: Test create 2 persons with rollback
      when we enter a transaction
      and we create a person called tux
      and we create a person called tuz
      and we rollback the transaction
      then we should not be able to get a person called tux
      and we should not be able to get a person called tuz
      and we should be able to find 0 persons

  Scenario: Test delete person
      when we create a person called tux
      and we enter a transaction
      and we delete a person called tux
      and we commit the transaction
      then we should not be able to get a person called tux
      and we should be able to find 0 persons

  Scenario: Test delete person with rollback
      when we create a person called tux
      and we enter a transaction
      and we delete a person called tux
      and we rollback the transaction
      then we should be able to get a person called tux
      and we should be able to find 1 persons
