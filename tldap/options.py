# Copyright 2012 VPAC
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

import re
import django.utils.translation
import tldap.helpers

get_verbose_name = lambda class_name: re.sub('(((?<=[a-z])[A-Z])|([A-Z](?![A-Z]|$)))', ' \\1', class_name).lower().strip()

DEFAULT_NAMES = ('verbose_name', 'verbose_name_plural',
                 'object_classes', 'search_classes', 'base_dn', 'base_dn_setting', 'pk')

class Options(object):
    def __init__(self, meta, app_label=None):
        self.module_name, self.verbose_name = None, None
        self.verbose_name_plural = None
        self.object_name, self.app_label = None, app_label
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
        self.module_name = self.object_name.lower()
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
                self.verbose_name_plural = django.utils.translation.string_concat(self.verbose_name, 's')

            # Any leftover attributes must be invalid.
            if meta_attrs != {}:
                raise TypeError("'class Meta' got invalid attribute(s): %s" % ','.join(meta_attrs.keys()))
        else:
            self.verbose_name_plural = django.utils.translation.string_concat(self.verbose_name, 's')

        del self.meta

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

