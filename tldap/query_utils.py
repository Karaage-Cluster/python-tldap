import six
import django.utils.tree


class Q(django.utils.tree.Node):
    """
    Encapsulates filters as objects that can then be combined logically
    (using ``&`` and ``|``).
    """
    # Connection types
    AND = 'AND'
    OR = 'OR'
    default = AND

    def __init__(self, *args, **kwargs):
        super(Q, self).__init__(
            children=list(args) + list(six.iteritems(kwargs)))

    def _combine(self, other, conn):
        if not isinstance(other, Q):
            raise TypeError(other)
        if len(self.children) < 1:
            self.connector = conn
        obj = type(self)()
        obj.connector = conn
        obj.add(self, conn)
        obj.add(other, conn)
        return obj

    def __or__(self, other):
        return self._combine(other, self.OR)

    def __and__(self, other):
        return self._combine(other, self.AND)

    def __invert__(self):
        obj = type(self)()
        obj.add(self, self.AND)
        obj.negate()
        return obj
