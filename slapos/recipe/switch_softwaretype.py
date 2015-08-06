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

import os, subprocess, sys

class Recipe:

  def __init__(self, buildout, name, options):
    self.buildout = buildout
    self.options = options
    self.name = name
    self.software_type = buildout["slap-configuration"]["slap-software-type"]
    section, key = self.options[self.software_type].split(":")
    self.base = self.buildout[section][key]

  def install(self):
    # XXX-Antoine: We gotta find a better way to do this. I tried to check
    # out how slapgrid-cp was running buildout. But it is worse than that.
    args = sys.argv[:]
    for x in self.buildout["slap-connection"].iteritems():
      args.append("slap-connection:%s=%s" % x)
    for x in "directory", "eggs-directory", "develop-eggs-directory":
      args.append("buildout:%s=%s" % (x, self.buildout["buildout"][x]))
    args.append("buildout:installed=.installed-%s.cfg" % self.name)
    # Options.get (from zc.buildout) should deserialize.
    try:
      override = self.options["override"][self.software_type]
    except (KeyError, TypeError):
      buildout = self.base
    else:
      # unfortunately, buildout:extends does not work when given at command line
      buildout = os.path.join(self.buildout["buildout"]["parts-directory"],
                              self.name + ".cfg")
      with open(override) as src, open(buildout, "w", 0) as dst:
        dst.write("[buildout]\nextends = %s\n\n" % self.base + src.read())
    subprocess.check_call(args + ["-oc", buildout])
    return []

  update = install
