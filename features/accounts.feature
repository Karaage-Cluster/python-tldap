Feature: Testing account functions

  Scenario: Test create account
      when we enter a transaction
      and we create a account called tux
      and we commit the transaction
      then we should be able to get a account called tux
      and we should be able confirm the cn attribute is Tux Torvalds
      and we should be able to find 1 accounts

  Scenario: Test create account with rollback
      when we enter a transaction
      and we create a account called tux
      and we rollback the transaction
      then we should not be able to get a account called tux
      and we should be able to find 0 accounts

  Scenario: Test create 2 accounts
      when we enter a transaction
      and we create a account called tux
      and we create a account called tuz
      and we commit the transaction
      then we should be able to get a account called tux
      and we should be able to get a account called tuz
      and we should be able to find 2 accounts

  Scenario: Test modify account
      when we create a account called tux
      and we enter a transaction
      and we modify a account called tux
      and we commit the transaction
      then we should be able to get a account called tux
      and we should be able confirm the cn attribute is Super Tux

  Scenario: Test modify account with rollback
      when we create a account called tux
      and we enter a transaction
      and we modify a account called tux
      and we rollback the transaction
      then we should be able to get a account called tux
      and we should be able confirm the cn attribute is Tux Torvalds

  Scenario: Test create 2 accounts with rollback
      when we enter a transaction
      and we create a account called tux
      and we create a account called tuz
      and we rollback the transaction
      then we should not be able to get a account called tux
      and we should not be able to get a account called tuz
      and we should be able to find 0 accounts

  Scenario: Test delete account
      when we create a account called tux
      and we enter a transaction
      and we delete a account called tux
      and we commit the transaction
      then we should not be able to get a account called tux
      and we should be able to find 0 accounts

  Scenario: Test delete account with rollback
      when we create a account called tux
      and we enter a transaction
      and we delete a account called tux
      and we rollback the transaction
      then we should be able to get a account called tux
      and we should be able to find 1 accounts
