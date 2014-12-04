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
import shutil

class Recipe:
  def __init__(self, buildout, name, options):
    self.buildout = buildout
    self.name = name
    self.options = options
    self.logger = logging.getLogger(self.name)

  def install(self):
    """
    Copy files to selected directory.
    """
    path_list = []
    target_directory = self.options['target-directory']
    for original_file_location in self.options['file-list'].split():
      path, name = os.path.split(original_file_location)
      destination_file_location = os.path.join(target_directory, name)
      if os.path.exists(destination_file_location):
        os.remove(destination_file_location)
      shutil.copy(original_file_location, destination_file_location)
      self.logger.debug('Created copy %r -> %r' % (
          original_file_location,
          destination_file_location))
      path_list.append(destination_file_location)

    return path_list
