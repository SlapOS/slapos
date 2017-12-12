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
import slapos.grid.utils
import tempfile
import unittest

class TestGridUtils(unittest.TestCase):

  def test_check_promise_success(self):
    """
      check that checkPromiseList works well
    """
    script = """#!/bin/sh
echo "%(name)s"
exit %(code)s
"""
    root_directory = tempfile.mkdtemp()
    promise_1 = "first_promise"
    promise_2 = "second_promise"
    promise_timeout = 10
    with open(os.path.join(root_directory, promise_1), 'w') as f:
      f.write(script % {'name': promise_1, 'code': 0})

    with open(os.path.join(root_directory, promise_2), 'w') as f:
      f.write(script % {'name': promise_2, 'code': 0})

    for file in os.listdir(root_directory):
      if 'promise' in file:
        os.chmod(os.path.join(root_directory, file), 0755)

    result_list = []
    try:
      result_list = slapos.grid.utils.checkPromiseList(
          root_directory,
          promise_timeout,
          profile=True,
          raise_on_failure=True,
          logger=None)
    except slapos.grid.utils.PromiseError:
      self.fail("Unexpected raise of PromiseError in 'checkPromiseList()'")

    for result in result_list:
      self.assertEquals(result['returncode'], 0)
      self.assertTrue(result['message'].strip() in [promise_1, promise_2])

  def test_check_promise_failure(self):
    """
      check that checkPromiseList works well
    """
    script = """#!/bin/sh
echo "%(name)s"
exit %(code)s
"""
    root_directory = tempfile.mkdtemp()
    promise_1 = "first_promise"
    promise_2 = "second_promise_fail"
    promise_timeout = 10
    with open(os.path.join(root_directory, promise_1), 'w') as f:
      f.write(script % {'name': promise_1, 'code': 0})

    with open(os.path.join(root_directory, promise_2), 'w') as f:
      f.write(script % {'name': promise_2, 'code': 1})

    for file in os.listdir(root_directory):
      if 'promise' in file:
        os.chmod(os.path.join(root_directory, file), 0755)

    with self.assertRaises(slapos.grid.utils.PromiseError):
      slapos.grid.utils.checkPromiseList(
        root_directory,
        promise_timeout,
        profile=True,
        raise_on_failure=True,
        logger=None)

  def test_check_promise_no_raise(self):
    """
      check that checkPromiseList works well
    """
    script = """#!/bin/sh
echo "%(name)s"
exit %(code)s
"""
    root_directory = tempfile.mkdtemp()
    promise_1 = "first_promise"
    promise_2 = "second_promise"
    promise_3 = "third_promise"
    promise_4 = "fourth_promise_fail"
    promise_timeout = 10
    with open(os.path.join(root_directory, promise_1), 'w') as f:
      f.write(script % {'name': promise_1, 'code': 0})

    with open(os.path.join(root_directory, promise_2), 'w') as f:
      f.write(script % {'name': promise_2, 'code': 0})

    with open(os.path.join(root_directory, promise_3), 'w') as f:
      f.write(script % {'name': promise_3, 'code': 0})

    with open(os.path.join(root_directory, promise_4), 'w') as f:
      f.write(script % {'name': promise_4, 'code': 1})

    for file in os.listdir(root_directory):
      if 'promise' in file:
        os.chmod(os.path.join(root_directory, file), 0755)

    result_list = []
    try:
      result_list = slapos.grid.utils.checkPromiseList(
          root_directory,
          promise_timeout,
          profile=True,
          raise_on_failure=False,
          logger=None)
    except slapos.grid.utils.PromiseError:
      self.fail("Unexpected raise of PromiseError in 'checkPromiseList()'")

    for result in result_list:
      self.assertTrue(result['message'].strip() in [promise_1, promise_2, promise_3, promise_4])
      if result['title'] == promise_4:
        self.assertEquals(result['returncode'], 1)
      else:
        self.assertEquals(result['returncode'], 0)

if __name__ == '__main__':
  unittest.main()
