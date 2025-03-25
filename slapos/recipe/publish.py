##############################################################################
#
# Copyright (c) 2010 Vifib SARL and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
from __future__ import print_function
import zc.buildout
from slapos.recipe.librecipe import wrap
from slapos.recipe.librecipe import GenericSlapRecipe
import six
import os
import traceback

CONNECTION_PARAMETER_STRING = 'connection-'

class Recipe(GenericSlapRecipe):
  return_list = []
  def __init__(self, buildout, name, options):
    super(Recipe, self).__init__(buildout, name, options)
    # Tell buildout about the sections we will access during install.
    self._extend_set = done = set()
    extends = [self.name]
    while extends:
      name = extends.pop()
      done.add(name)
      extends += set(self.buildout[name].get('-extends', '').split()) - done

  def _install(self):
    publish_dict = {}
    for name in self._extend_set:
      section = self.buildout[name]
      try:
        publish = section['-publish'].split()
      except KeyError:
        publish = (k for k in section
          if k != 'recipe' and not k.startswith('-'))
      for k in publish:
        publish_dict[k] = section[k]
    self._setConnectionDict(publish_dict, self.options.get('-slave-reference'))
    return self.return_list

  def _setConnectionDict(self, publish_dict, slave_reference=None):
    return self.setConnectionDict(publish_dict, slave_reference)

class Serialised(Recipe):
  def _setConnectionDict(self, publish_dict, slave_reference=None):
    return super(Serialised, self)._setConnectionDict(wrap(publish_dict), slave_reference)


class Failsafe(object):
  def _setConnectionDict(self, publish_dict, slave_reference):
    error_status_file = self.options.get('-error-status-file')
    # Note: We can't put -error-status-file in return list as by default it is
    #       not present, and buildout wants the section to have it, so it
    #       Uninstalls/Installs the part instead of just Updating it
    self.return_list = []
    try:
      super(Failsafe, self)._setConnectionDict(publish_dict, slave_reference)
    except Exception:
      if error_status_file is not None:
        with open(error_status_file, 'w') as fh:
          fh.write(traceback.format_exc())
    else:
      if error_status_file is not None:
        if os.path.exists(error_status_file):
          os.unlink(error_status_file)

  def update(self):
    error_status_file = self.options.get('-error-status-file')
    if error_status_file is not None:
      if os.path.exists(error_status_file):
        # last run failed, so need to reinstall
        self.install()

  def uninstall(name, options):
    error_status_file = options.get('-error-status-file')
    if error_status_file is not None:
      if os.path.exists(error_status_file):
        os.unlink(error_status_file)


class RecipeFailsafe(Failsafe, Recipe):
  pass


class SerialisedFailsafe(Failsafe, Serialised):
  pass
