##############################################################################
#
# Copyright (c) 2014 Vifib SARL and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
##############################################################################

from zc.buildout.buildout import Buildout, MissingOption, MissingSection
from zc.buildout import UserError

class SubBuildout(Buildout):
  """Run buildout in buildout, partially copied from infrae.buildout
  """
  def __init__(self, main_buildout, config, options, **kwargs):
    # Use same logger
    self._logger = main_buildout._logger
    self._log_level = main_buildout._log_level

    # Use same options
    for opt in (
        'offline',
        'verbosity',
        'newest',
        'directory',
        'eggs-directory',
        'develop-eggs-directory',
    ):
      if opt in main_buildout['buildout']:
        options.append((
            'buildout',
            opt,
            main_buildout['buildout'][opt],
        ))
    # Use same slap connection
    for k, v in main_buildout["slap-connection"].items():
      options.append(('slap-connection', k, v))

    Buildout.__init__(self, config, options, **kwargs)

  def _setup_logging(self):
    """We don't want to setup any logging, since it's already done
    by the main buildout.
    """
    pass


class Recipe:

  def __init__(self, buildout, name, options):
    self.buildout = buildout
    self.options = options
    self.name = name
    try:
      self.software_type = buildout["slap-configuration"]["slap-software-type"]
    except (MissingSection, MissingOption):
      raise UserError("The section to retrieve slap partition parameters "
                      "(with slapos.cookbook:slapconfiguration recipe or a derived one) "
                      "must be named [slap-configuration].")
    try:
      section, key = self.options[self.software_type].split(":")
    except MissingOption:
      raise MissingOption("This software type (%s) isn't mapped. RootSoftwareInstance "
                      "is the default software type." % self.software_type)
    except ValueError:
      raise UserError("The software types in the section [%s] must be separated "
                      "by a colon such as: 'section:key', where key is usually 'rendered'. "
                      "Don't use: ${section:key}" % self.name)
    self.base = self.buildout[section][key]

  def install(self):
    options = [("buildout", "installed", ".installed-%s.cfg" % self.name)]
    profile = self.base
    try:
      # XXX this assume using slapos.buildout, which serializes arbitrary python objects for options
      extended_profile = self.options["override"][self.software_type]
    except (KeyError, TypeError):
      pass
    else:
      options.append(["buildout", "extends", profile])
      profile = extended_profile

    sub_buildout = SubBuildout(
        self.buildout,
        profile,
        options,
    )

    sub_buildout.install([])

  update = install
