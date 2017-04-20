# Copyright 2012-2014 Brian May
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

""" Contains the options class, which represents a list of options associated
with a tldap object. """
from __future__ import absolute_import

import re
import warnings
import tldap.helpers


def get_verbose_name(class_name):
    return re.sub(
        '(((?<=[a-z])[A-Z])|([A-Z](?![A-Z]|$)))', ' \\1',
        class_name).lower().strip()


DEFAULT_NAMES = ('verbose_name', 'verbose_name_plural',
                 'object_classes', 'search_classes', 'base_dn',
                 'base_dn_setting', 'pk')


class Options(object):
    """ Contains a list of options associated with a tldap object. """
    def __init__(self, meta):
        self.model_name, self.verbose_name = None, None
        self.verbose_name_plural = None
        self.object_name = None
        self.meta = meta
        self._fields = tldap.helpers.CaseInsensitiveDict()
        self.object_classes = set()
        self.search_classes = set()
        self.base_dn = None
        self.base_dn_setting = None
        self.pk = None

    def contribute_to_class(self, cls, name):
        setattr(cls, name, self)

        self.object_name = cls.__name__
        self.model_name = self.object_name.lower()
        self.verbose_name = get_verbose_name(self.object_name)

        if self.meta:
            meta_attrs = self.meta.__dict__.copy()
            for name in self.meta.__dict__:
                # Ignore any private attributes that Django doesn't care about.
                # NOTE: We can't modify a dictionary's contents while looping
                # over it, so we loop over the *original* dictionary instead.
                if name.startswith('_'):
                    del meta_attrs[name]
            for attr_name in DEFAULT_NAMES:
                if attr_name in meta_attrs:
                    setattr(self, attr_name, meta_attrs.pop(attr_name))
                elif hasattr(self.meta, attr_name):
                    setattr(self, attr_name, getattr(self.meta, attr_name))

            # verbose_name_plural is a special case because it uses a 's'
            # by default.
            if self.verbose_name_plural is None:
                self.verbose_name_plural = self.verbose_name + 's'

            # Any leftover attributes must be invalid.
            if meta_attrs != {}:
                raise TypeError(
                    "'class Meta' got invalid attribute(s): %s" %
                    ','.join(meta_attrs.keys()))
        else:
            self.verbose_name_plural = self.verbose_name + 's'

        del self.meta

    @property
    def module_name(self):
        """
        This property has been deprecated in favor of `model_name`. refs django
        #19689
        """
        warnings.warn(
            "Options.module_name has been deprecated in favor of model_name",
            PendingDeprecationWarning, stacklevel=2)
        return self.model_name

    def add_field(self, field):
        self._fields[field.name] = field

    def get_field_by_name(self, name):
        return self._fields[name]

    def get_field_name(self, name):
        """ get the field name with the correct case. """
        return self._fields.get_correct_key(name)

    def get_all_field_names(self):
        return set(self._fields.keys())

    @property
    def fields(self):
        return self._fields.values()
