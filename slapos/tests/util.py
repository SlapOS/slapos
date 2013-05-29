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
import os
import slapos.util
import tempfile
import unittest


class TestMkdirP(unittest.TestCase):
  """
  Tests methods available in the slapos.util module.
  """

  def test_mkdir_p_new_directory(self):
    """
    Test that mkdir_p recursively creates a directory.
    """
    root_directory = tempfile.mkdtemp()
    wanted_directory = os.path.join(root_directory, 'foo', 'bar')
    slapos.util.mkdir_p(wanted_directory)
    self.assertTrue(os.path.isdir(wanted_directory))

  def test_mkdir_already_existing(self):
    """
    Check that mkdir_p doesn't raise if directory already exist.
    """
    root_directory = tempfile.mkdtemp()
    slapos.util.mkdir_p(root_directory)
    self.assertTrue(os.path.isdir(root_directory))


if __name__ == '__main__':
  unittest.main()
