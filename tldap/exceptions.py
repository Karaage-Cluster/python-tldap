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

class TestFailure(Exception):
    """Simulated failure for testing."""
    pass

class FieldError(Exception):
    """Some kind of problem with a field."""
    pass

class ObjectDoesNotExist(Exception):
    "The requested object does not exist"
    silent_variable_failure = True

class MultipleObjectsReturned(Exception):
    "The query returned multiple objects when only one was expected."
    pass

class ValidationError(Exception):
    """An error while validating data."""
    pass

class DatabaseError(Exception):
    """An error while validating data."""
    pass
