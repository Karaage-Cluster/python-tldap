from features.steps.utils import do_config

import behave

from tldap import transaction


@behave.given(u'we login as {DN} using {password}')
def step_login(context, DN, password):
    """ Test if we can logon correctly with correct password. """
    do_config(DN, password)


@behave.when(u'we enter a transaction')
def step_start_transaction(context):
    transaction.enter_transaction_management()


@behave.when(u'we commit the transaction')
def step_commit_transaction(context):
    transaction.commit()
    transaction.leave_transaction_management()


@behave.when(u'we rollback the transaction')
def step_rollback_transaction(context):
    transaction.rollback()
    transaction.leave_transaction_management()


@behave.then(u'we should be able confirm the {attribute} attribute is {value}')
def step_confirm_attribute(context, attribute, value):
    actual_value = getattr(context.obj, attribute)
    assert str(actual_value) == value
