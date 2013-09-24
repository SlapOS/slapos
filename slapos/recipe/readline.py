# vim: set et sts=2:
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

import errno

class Recipe(object):
  """Read the first line of a file.

  As the result has to be provided as an options, it is mandatory that the
  buildout profile fills the file content (if needed) before trying to read it.

    Options:
    - storage-path: file to read

    Result set in options:
    - readline: first line of the file
  """

  def __init__(self, buildout, name, options):
    storage_path = options['storage-path']
    try:
      with open(storage_path) as f:
        readline = f.readline()
    except IOError, e:
      if e.errno != errno.ENOENT:
        raise
      readline = None

    self.readline = readline
    options['readline'] = readline

  def install(self):
    if self.readline is None:
      raise ValueError('Unable to read the file content.')
    return ()

  def update(self):
    return ()
