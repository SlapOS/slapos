# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Vifib SARL and Contributors. All Rights Reserved.
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import os
import shutil
from slapos.cli_legacy import entry
import sys
import tempfile
import unittest


class BasicMixin:

  def setUp(self):
    self._tempdir = tempfile.mkdtemp()
    self._original_sys_argv = sys.argv
    sys.argv = ['entry']

  def tearDown(self):
    shutil.rmtree(self._tempdir, True)
    sys.argv = self._original_sys_argv


class TestcheckSlaposCfg (BasicMixin, unittest.TestCase):
  """
  Tests on checkSlaposCfg function
  """

  def test_slapos_cfg_detection_when_no_configuration_given(self):
    """
    If no configuration file is given then False is return
    """
    sys.argv = ['entry', '--logfile', '/log/file']
    self.assertFalse(entry.checkSlaposCfg())

  def test_slapos_cfg_detection_when_file_does_not_exists(self):
    """
    If given configuration file does not exists then False is return
    """
    slapos_cfg = os.path.join(self._tempdir, 'slapos.cfg')
    sys.argv = ['entry', slapos_cfg]
    self.assertFalse(entry.checkSlaposCfg())

  def test_slapos_cfg_detection_when_no_slapos_section(self):
    """
    If given configuration file does not have slapos section
    then False is return
    """
    slapos_cfg = os.path.join(self._tempdir, 'slapos.cfg')
    open(slapos_cfg, 'w').write('[slapformat]')
    sys.argv = ['entry', slapos_cfg]
    self.assertFalse(entry.checkSlaposCfg())

  def test_slapos_cfg_detection_when_correct(self):
    """
    If given configuration file have slapos section
    then True is return
    """
    slapos_cfg = os.path.join(self._tempdir, 'slapos.cfg')
    open(slapos_cfg, 'w').write('[slapos]')
    sys.argv.append(slapos_cfg)
    self.assertTrue(entry.checkSlaposCfg())


class TestcheckOption (BasicMixin, unittest.TestCase):

  def test_present_option_is_not_added(self):
    """
    If the option is already there do not add it
    """
    sys.argv += ['-vc', '--logfile', '/opt/slapos/slapos.log']
    original_sysargv = sys.argv
    entry.checkOption("--logfile /opt/slapos/format.log")
    self.assertEqual(original_sysargv, sys.argv)

  def test_missing_option_is_added(self):
    """
    If the option is not there add it
    """
    sys.argv += ['-vc', '--pidfile', '/opt/slapos/slapos.pid']
    original_sysargv = sys.argv
    option = "--logfile /opt/slapgrid/slapformat.log"
    entry.checkOption(option)
    self.assertNotEqual(original_sysargv, sys.argv)
    self.assertTrue(option in " ".join(sys.argv))


class TestCall (BasicMixin, unittest.TestCase):
  """
  Testing call function
  """
  def test_config_and_option_are_added(self):
    """
    Test missing options and config are added
    """
    sys.argv += ['-vc']
    original_sysargv = sys.argv

    def fun():
      return 0

    options = ["--logfile /opt/slapos/logfile",
               "--pidfile /opt/slapos/pidfile"]
    config_path = '/etc/opt/slapos/slapos.cfg'
    try:
      entry.call(fun, config_path=config_path, option=options)
    except SystemExit, e:
      self.assertEqual(e[0], 0)
    self.assertNotEqual(original_sysargv, sys.argv)
    for x in options:
      self.assertTrue(x in " ".join(sys.argv))
    self.assertEqual(config_path, sys.argv[1])

  def test_config_and_missing_option_are_added(self):
    """
    Test missing options and config are added but do not replace
    already present option
    """
    missing_option = "--logfile /opt/slapos/logfile"
    present_option = "--pidfile /opt/slapos/pidfile"
    default_present_option = "--pidfile /opt/slapos/pidfile.default"
    sys.argv += ['-vc', present_option]
    original_sysargv = sys.argv

    def fun():
      return 0

    options = [default_present_option, missing_option]
    config_path = '/etc/opt/slapos/slapos.cfg'
    try:
      entry.call(fun, config_path=config_path, option=options)
    except SystemExit, e:
      self.assertEqual(e[0], 0)
    self.assertNotEqual(original_sysargv, sys.argv)
    for x in (missing_option, present_option):
      self.assertTrue(x in " ".join(sys.argv))
    self.assertFalse(default_present_option in " ".join(sys.argv))
    self.assertEqual(config_path, sys.argv[1])

  def test_present_config_and_option_are_not_added(self):
    """
    Test already present options and config are not added
    """
    present_option = "--pidfile /opt/slapos/pidfile"
    default_present_option = "--pidfile /opt/slapos/pidfile.default"
    slapos_cfg = os.path.join(self._tempdir, 'slapos.cfg')
    open(slapos_cfg, 'w').write('[slapos]')
    sys.argv += ['-vc', slapos_cfg, present_option.split()[0],
                 present_option.split()[1]]
    original_sysargv = sys.argv

    def fun():
      return 0

    options = [default_present_option]
    config_path = '/etc/opt/slapos/slapos.cfg'
    try:
      entry.call(fun, config_path=config_path, option=options)
    except SystemExit, e:
      self.assertEqual(e[0], 0)

    self.assertEqual(original_sysargv, sys.argv)
