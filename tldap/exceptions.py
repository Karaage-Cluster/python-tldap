# Copyright 2012-2014 VPAC
#
# This file is part of django-tldap.
#
# django-tldap is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# django-tldap is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with django-tldap  If not, see <http://www.gnu.org/licenses/>.


class InvalidDN(Exception):
    """ DN value is invalid and cannot be parsed. """


class TestFailure(Exception):
    """Simulated failure for testing."""
    pass


class FieldError(Exception):
    """Some kind of problem with a field."""
    pass


class ObjectDoesNotExist(Exception):
    "The requested object does not exist"
    pass


class MultipleObjectsReturned(Exception):
    "The query returned multiple objects when only one was expected."
    pass


class ObjectAlreadyExists(Exception):
    "The requested object already exists"
    pass


class ValidationError(Exception):
    """An error while validating data."""
    pass


class RollbackError(Exception):
    """An error in rollback and consistency cannot be guaranteed."""
    pass
