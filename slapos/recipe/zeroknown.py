##############################################################################
#
# Copyright (c) 2013 Vifib SARL and Contributors. All Rights Reserved.
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

import ConfigParser
import os
import zc.buildout

from slapos.recipe.librecipe import GenericBaseRecipe


class WriteRecipe(GenericBaseRecipe):
  """
  """
  def __init__(self, buildout, name, options):
    if not "filename" in options:
      raise zc.buildout.UserError("You have to provide the parameter \"filename\"")

    self.filename = options['filename'].strip()
    self.path = os.path.join(buildout['buildout']['directory'], self.filename)
    self.name = name
    self.options = options.copy()
    del self.options['filename']
    del self.options['recipe']

    # Set up the parser, and write config file if needed
    self.parser = ConfigParser.ConfigParser()
    try:
      self.parser.read(self.path)
      #clean_options(options)
      for key in self.options:
        if key not in self.parser.options(self.name):
          self.parser.set(self.name, key, self.options[key])
      with open(self.path, 'w') as file:
        self.parser.write(file)
    # If the file or section do not exist
    except (ConfigParser.NoSectionError, IOError) as e:
      self.full_install()

  install = update = lambda self: []

  def full_install(self):
    """XXX-Nicolas : when some parameter's value is changed in
    buildout profile, this will override custom user defined values"""
    self.parser.read(self.path)
    if self.parser.has_section(self.name):
      self.parser.remove_section(self.name)
    self.parser.add_section(self.name)
    for key in self.options:
      self.parser.set(self.name, key, self.options[key])
    with open(self.path, 'w') as file:
      self.parser.write(file)


class ReadRecipe(GenericBaseRecipe):
  """
  """
  def __init__(self, buildout, name, options):
    if not "filename" in options:
      raise zc.buildout.UserError("You have to provide the parameter \"filename\"")

    self.filename = options['filename'].strip()
    self.path = os.path.join(buildout['buildout']['directory'], self.filename)

    # Set up the parser, and write config file if needed
    self.parser = ConfigParser.ConfigParser()
    if os.path.exists(self.path):
      self.parser.read(self.path)
      for section in self.parser.sections():
        for key ,value in self.parser.items(section):
            options[key] = value

  install = update = lambda self: []
