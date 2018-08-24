##############################################################################
#
# Copyright (c) 2018 Vifib SARL and Contributors. All Rights Reserved.
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
import sys
import tempfile
import unittest
import logging
import mock


import slapos.grid.utils


class SlapPopenTestCase(unittest.TestCase):
  def setUp(self):
    self.script = tempfile.NamedTemporaryFile(delete=False)
    # make executable
    os.chmod(self.script.name, 0o777)

  def tearDown(self):
    os.unlink(self.script.name)

  def test_exec(self):
    """Test command execution with SlapPopen.
    """
    self.script.write('#!/bin/sh\necho "hello"\nexit 123')
    self.script.close()

    logger = mock.MagicMock()
    program = slapos.grid.utils.SlapPopen(
        self.script.name,
        logger=logger)

    # error code and output are returned
    self.assertEqual(123, program.returncode)
    self.assertEqual('hello\n', program.output)

    # output is also logged "live"
    logger.info.assert_called_with('hello')

  def test_debug(self):
    """Test debug=True, which keeps interactive.
    """
    self.script.write('#!/bin/sh\necho "exit code?"\nread rc\nexit $rc')
    self.script.close()

    # keep a reference to stdin and stdout to restore them later
    stdin_backup = os.dup(sys.stdin.fileno())
    stdout_backup = os.dup(sys.stdout.fileno())

    # replace stdin with a pipe that will write 123
    child_stdin_r, child_stdin_w = os.pipe()
    os.write(child_stdin_w, "123")
    os.close(child_stdin_w)
    os.dup2(child_stdin_r, sys.stdin.fileno())

    # and stdout with the pipe to capture output
    child_stdout_r, child_stdout_w = os.pipe()
    os.dup2(child_stdout_w, sys.stdout.fileno())

    try:
      program = slapos.grid.utils.SlapPopen(
          self.script.name,
          debug=True,
          logger=logging.getLogger())
      # program output
      self.assertEqual('exit code?\n', os.read(child_stdout_r, 1024))

      self.assertEqual(123, program.returncode)
      self.assertEqual('(output not captured in debug mode)', program.output)
    finally:
      # restore stdin & stderr
      os.dup2(stdin_backup, sys.stdin.fileno())
      os.dup2(stdout_backup, sys.stdout.fileno())
      # close all fds open for the test
      for fd in (child_stdin_r, child_stdout_r, child_stdout_w, stdin_backup, stdout_backup):
        os.close(fd)


