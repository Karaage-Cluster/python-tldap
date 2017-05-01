Future work
===========

*   Some servers, e.g. Active Directory, support transactions properly in the
    server. Need to support these transactions natively.

*   The Active Directory primary group field type has never been implemented
    correctly for the entire set of operations. This is due to the complicated
    nature of some of the side effects when dealing with this field.

*   Initial tests seem to indicate that the account locking/unlocking code for
    Directory Server 389 does not lock the account. Need to fix this.
