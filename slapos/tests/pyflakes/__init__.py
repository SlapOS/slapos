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
import pkg_resources
import pyflakes.scripts.pyflakes
import sys
import unittest

class CheckCodeConsistency(unittest.TestCase):
  """Lints all SlapOS Node and SLAP library code base."""
  def setUp(self):
    self._original_argv = sys.argv
    sys.argv = [sys.argv[0],
                os.path.join(
                    pkg_resources.get_distribution('slapos.core').location,
                    'slapos',
                )
               ]

  def tearDown(self):
    sys.argv = self._original_argv

  @unittest.skip('pyflakes test is disabled')
  def testCodeConsistency(self):
    if pyflakes.scripts.pyflakes.main.func_code.co_argcount:
      pyflakes.scripts.pyflakes.main([
                os.path.join(
                    pkg_resources.get_distribution('slapos.core').location,
                    'slapos',
                )])
    else:
      pyflakes.scripts.pyflakes.main()

