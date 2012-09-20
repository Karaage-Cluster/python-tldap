# Copyright 2012 VPAC
#
# This file is part of python-tldap.
#
# python-tldap is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# python-tldap is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with python-tldap  If not, see <http://www.gnu.org/licenses/>.

import tldap.exceptions

class Field(object):
    def __init__(self, max_instances=1, required=False):
        self._max_instances = max_instances
        self._required = required

    def contribute_to_class(self, cls, name):
        self.name = name
        self._cls = cls
        cls._meta.add_field(self)

    def to_db(self, value):
        "returns field's value prepared for saving into a database."

        # ensure value is valid
        self.validate(value)

        # ensure value is a new list. We have to make a copy, as
        # we will be changing it.
        if value is None:
            value = []
        elif isinstance(value, str):
            value = [value]
        else:
            value = list(value)

        # convert every value in list
        for i,v in enumerate(value):
            value[i] = self.value_to_db(v)

        # return result
        return value

    def to_python(self, value):
        """
        Converts the input value into the expected Python data type, raising
        django.core.exceptions.ValidationError if the data can't be converted.
        Returns the converted value. Subclasses should override this.
        """

        # convert every value in list
        for i,v in enumerate(value):
            value[i] = self.value_to_python(v)

        # if we only expect one value, see if we can remove list
        if self._max_instances is not None:
            if self._max_instances == 1:
                if len(value) == 0:
                    value = None
                elif len(value) == 1:
                    value = value[0]

        # return result
        return value

    def validate(self, value):
        """
        Validates value and throws ValidationError. Subclasses should override
        this to provide validation logic.
        """

        # ensure value is a list
        if value is None:
            value = []
        elif isinstance(value, str):
            value = [ value ]

        # validate every item in list
        for v in value:
            self.value_validate(v)

        # check this required value is given
        if self._required:
            if value is None or len(value)==0:
                raise tldap.exceptions.ValidationError("%r is required"%self.name)

        # check max_instances not exceeded
        if self._max_instances is not None:
            if len(value) > self._max_instances:
                raise tldap.exceptions.ValidationError("%r is has more then %d values"%(self.name, self._max_instances))

    def clean(self, value):
        """
        Convert the value's type and run validation. Validation errors from to_python
        and validate are propagated. The correct value is returned if no error is
        raised.
        """
        value = self.to_python(value)
        self.validate(value)
        return value

    def value_to_db(self, value):
        "returns field's single value prepared for saving into a database."
        return value

    def value_to_python(self, value):
        """
        Converts the input single value into the expected Python data type, raising
        django.core.exceptions.ValidationError if the data can't be converted.
        Returns the converted value. Subclasses should override this.
        """
        return value

    def value_validate(self, value):
        """
        Validates value and throws ValidationError. Subclasses should override
        this to provide validation logic.
        """
        pass


class CharField(Field):
    pass

class IntegerField(Field):
    def value_to_python(self, value):
        """
        Converts the input single value into the expected Python data type, raising
        django.core.exceptions.ValidationError if the data can't be converted.
        Returns the converted value. Subclasses should override this.
        """
        if value is None:
            return value
        try:
            return int(value)
        except (TypeError, ValueError):
            raise tldap.exceptions.ValidationError("%r is invalid integer"%self.name)

    def value_validate(self, value):
        """
        Converts the input single value into the expected Python data type, raising
        django.core.exceptions.ValidationError if the data can't be converted.
        Returns the converted value. Subclasses should override this.
        """
        if value is None:
            return value
        try:
            return str(int(value))
        except (TypeError, ValueError):
            raise tldap.exceptions.ValidationError("%r is invalid integer"%self.name)
