##############################################################################
#
# Copyright (c) 2017 Vifib SARL and Contributors. All Rights Reserved.
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
"""
Recipe to create a service with more fine-grained control than creating a
wrapper in etc/service.


"""

import textwrap
import os
import os.path

from slapos.recipe.wrapper import Recipe as Wrapper
from slapos.recipe.librecipe import GenericBaseRecipe


class Recipe(Wrapper):
  """Create group and program inside etc/supervisor.d directory."""

  def install(self):
    """Create wrapper but fine-control its execution."""
    if "etc/run" in self.options['wrapper-path']:
      raise ValueError("Service should not be placed into etc/run")
    if "etc/service" in self.options['wrapper-path']:
      raise ValueError("Service should not be placed into etc/service")

    scripts = super(Recipe, self).install()
    executable = scripts[-1]

    # name was set by the contructor into self.name
    priority = int(self.options.get("priority", 100))
    supervisor_d = self.options.get("supervisor.d") or os.path.join(
      self.buildout['buildout']['directory'], "..", "etc", "supervisord.conf.d")

    if ":" in self.name:
      raise ValueError("Service.name must not contain colon!")

    return scripts + [
      self.createFile(
        os.path.join(supervisor_d, "{}.conf".format(self.name)),
        textwrap.dedent("""
          [program:{}]
          command = {}
          priority = {:d}
          """.format(self.name, executable, priority)))]


class GroupRecipe(GenericBaseRecipe):
  """Create a supervisors' group for programs."""

  def install(self):
    """Create file representing group.

    programs must be a string with comma-separated values.
    More info: http://supervisord.org/configuration.html#group-x-section-settings
    """
    programs = self.options['programs'].replace(",", " ").split()
    priority = int(self.options.get('priority', 100))
    supervisor_d = self.options.get("supervisor.d") or os.path.join(
      self.buildout['buildout']['directory'], "..", "etc", "supervisord.conf.d")

    return [self.createFile(
      os.path.join(supervisor_d, "{}.conf".format(self.name)),
      textwrap.dedent("""
        [group:{}]
        programs = {}
        priority = {:d}
        """.format(self.name, ",".join(programs), priority))
    )]
