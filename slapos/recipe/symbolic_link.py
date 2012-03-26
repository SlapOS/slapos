##############################################################################
#
# Copyright (c) 2011 Vifib SARL and Contributors. All Rights Reserved.
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
import os
import logging

class Recipe:
  def __init__(self, buildout, name, options):
    self.buildout = buildout
    self.name = name
    self.options = options
    self.logger = logging.getLogger(self.name)

  def install(self):
    """
    Links binaries to instance's bin directory for easier exposal
    """
    path_list = []
    target_directory = self.options['target-directory']
    for linkline in self.options['link-binary'].split():
      path, linkname = os.path.split(linkline)

      link = os.path.join(target_directory, linkname)
      if os.path.lexists(link):
        if not os.path.islink(link):
          raise zc.buildout.UserError(
              'Target link already %r exists but it is not link' % link)
        os.unlink(link)
      os.symlink(linkline, link)
      self.logger.debug('Created link %r -> %r' % (link, linkline))
      path_list.append(link)

    return path_list
