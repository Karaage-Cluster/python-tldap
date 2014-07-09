import warnings
warnings.warn(
    'tldap.backend.transaction obsolete; '
    'use tldap.backend.fake_transactions instead.',
    DeprecationWarning
)

from tldap.backend.fake_transactions import *  # NOQA
