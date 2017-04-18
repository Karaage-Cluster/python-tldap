try:
    from ldap3 import SIMPLE
except ImportError:
    from ldap3 import AUTH_SIMPLE as SIMPLE  # noqa

try:
    from ldap3 import BASE
except ImportError:
    from ldap3 import SEARCH_SCOPE_BASE_OBJECT as BASE  # noqa

try:
    from ldap3 import LEVEL
except ImportError:
    from ldap3 import SEARCH_SCOPE_SINGLE_LEVEL as LEVEL  # noqa

try:
    from ldap3 import SUBTREE
except ImportError:
    from ldap3 import SEARCH_SCOPE_WHOLE_SUBTREE as SUBTREE  # noqa
