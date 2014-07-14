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

""" tldap.methods is a set of classes to assist manipulating attributes in a
generic way. """

import tldap.base
import warnings
from django.utils.encoding import python_2_unicode_compatible

# This code requires django, so initialize Django
import tldap.django


@python_2_unicode_compatible
class baseMixin(tldap.base.LDAPobject):
    """ Base class, all objects should inherit from this instead of
    :py:class:`tldap.base.LDAPobject`. """

    mixin_list = []
    """ Class variable to be overriden for class that provides a list of mixins
    supported. """

    def __init__(self, **kwargs):
        super(baseMixin, self).__init__(**kwargs)
        # We must have our settings.
        assert self._settings is not None

    @classmethod
    def get_default_base_dn(cls, using, settings):
        """ Get the default base_dn for this *class*.

        :param cls: This class.
        :param using: The LDAP database alias.
        :param settings: A set of parameters.
        :return: Fully qualified base dn. May be None if unsuccessful.

        This class will lookup the base_dn in settings if the base method
        couldn't get a result.
        """

        # Call superclass, and try to get base. Was it successful?
        base_dn = super(baseMixin, cls).get_default_base_dn(using, settings)

        # If no, was it provided as a setting?
        if base_dn is None and settings is not None:
            key = cls._meta.base_dn_setting
            assert key in settings
            if key in settings:
                base_dn = settings[key]

        # If we still haven't got it, we failed.
        return base_dn

    def change_password(self, password):
        for mixin in self.mixin_list:
            if hasattr(mixin, 'change_password'):
                mixin.change_password(self, password)

    def set_defaults(self):
        # depreciated
        warnings.warn(
            "The use of set_defaults() has been deprecated.",
            DeprecationWarning)

    def pre_create(self, master):
        warnings.warn(
            "The use of pre_create() has been deprecated. "
            "Use setup_from_master() if required instead.",
            DeprecationWarning)
        if master is not None:
            self.setup_from_master(master)

    def post_create(self, master):
        # depreciated
        warnings.warn(
            "The use of pre_create() has been deprecated.",
            DeprecationWarning)
        pass

    def pre_save(self):
        warnings.warn(
            "The use of pre_save() has been deprecated.",
            DeprecationWarning)
        # depreciated
        pass

    def setup_from_master(self, master):
        self._master = master
        for mixin in self.mixin_list:
            if hasattr(mixin, 'setup_from_master'):
                mixin.setup_from_master(self, master)

    def _add(self):
        for mixin in self.mixin_list:
            if hasattr(mixin, 'pre_create'):
                warnings.warn(
                    "The use of pre_create() in mixin has been deprecated. "
                    "Use pre_add() instead. ",
                    DeprecationWarning)
                mixin.pre_create(self, self._master)
            if hasattr(mixin, 'pre_add'):
                mixin.pre_add(self)
            if hasattr(mixin, 'pre_save'):
                mixin.pre_save(self)
        super(baseMixin, self)._add()
        for mixin in self.mixin_list:
            if hasattr(mixin, 'post_add'):
                mixin.post_add(self)
            if hasattr(mixin, 'post_save'):
                mixin.post_save(self)
            if hasattr(mixin, 'post_create'):
                warnings.warn(
                    "The use of post_create() in mixin has been deprecated. "
                    "Use post_add() instead. ",
                    DeprecationWarning)
                mixin.post_create(self, self._master)

    def _modify(self):
        for mixin in self.mixin_list:
            if hasattr(mixin, 'pre_modify'):
                mixin.pre_modify(self)
            if hasattr(mixin, 'pre_save'):
                mixin.pre_save(self)
        super(baseMixin, self)._modify()
        for mixin in self.mixin_list:
            if hasattr(mixin, 'post_modify'):
                mixin.post_modify(self)
            if hasattr(mixin, 'post_save'):
                mixin.post_save(self)

    def pre_delete(self):
        # depreciated
        pass

    def _delete(self):
        for mixin in self.mixin_list:
            if hasattr(mixin, 'pre_delete'):
                mixin.pre_delete(self)
        super(baseMixin, self)._delete()

    def lock(self):
        for mixin in self.mixin_list:
            if hasattr(mixin, 'lock'):
                mixin.lock(self)

    def unlock(self):
        for mixin in self.mixin_list:
            if hasattr(mixin, 'unlock'):
                mixin.unlock(self)

    def check_password(self, password):
        locked = True
        num = 0

        if self.is_locked():
            return False

        for mixin in self.mixin_list:
            if hasattr(mixin, 'check_password'):
                num = num + 1
                if not mixin.check_password(self, password):
                    locked = False

        if num == 0:
            locked = False

        return locked

    def is_locked(self):
        locked = True

        for mixin in self.mixin_list:
            if hasattr(mixin, 'is_locked'):
                if not mixin.is_locked(self):
                    locked = False

        return locked

    def __str__(self):
        for mixin in reversed(self.mixin_list):
            if hasattr(mixin, '__str__'):
                return mixin.__str__(self)
