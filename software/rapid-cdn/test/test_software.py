##############################################################################
#
# Copyright (c) 2025 Nexedi SA and Contributors. All Rights Reserved.
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
import sys
import tempfile
import unittest
from datetime import datetime
from datetime import timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import software


class TestCheckCdnNodeActivityCheck(unittest.TestCase):

  def _makeLogLine(self, timestamp, message='INFO - processing'):
    return '%s,000 - cdn-instance-node - %s\n' % (
      timestamp.strftime('%Y-%m-%d %H:%M:%S'), message)

  def test_missing_log_file(self):
    status, message = software.check_cdn_node_activity_check(
      '/nonexistent/path/log.txt')
    self.assertEqual(status, 'error')
    self.assertIn('does not exist', message)

  def test_empty_log_file(self):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log',
                                     delete=False) as f:
      f.write('')
      path = f.name
    try:
      status, message = software.check_cdn_node_activity_check(path)
      self.assertEqual(status, 'error')
      self.assertIn('empty', message)
    finally:
      os.unlink(path)

  def test_recent_activity(self):
    now = datetime.now()
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log',
                                     delete=False) as f:
      f.write(self._makeLogLine(now - timedelta(seconds=10)))
      path = f.name
    try:
      status, message = software.check_cdn_node_activity_check(path)
      self.assertEqual(status, 'ok')
      self.assertIn('active', message)
    finally:
      os.unlink(path)

  def test_stale_activity(self):
    old = datetime.now() - timedelta(seconds=600)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log',
                                     delete=False) as f:
      f.write(self._makeLogLine(old))
      path = f.name
    try:
      status, message = software.check_cdn_node_activity_check(path)
      self.assertEqual(status, 'error')
      self.assertIn('no recent activity', message)
    finally:
      os.unlink(path)

  def test_no_valid_timestamps(self):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log',
                                     delete=False) as f:
      f.write('some random log line without timestamps\n')
      f.write('another line\n')
      path = f.name
    try:
      status, message = software.check_cdn_node_activity_check(path)
      self.assertEqual(status, 'error')
      self.assertIn('Could not find a valid timestamp', message)
    finally:
      os.unlink(path)

  def test_future_timestamp(self):
    future = datetime.now() + timedelta(hours=1)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log',
                                     delete=False) as f:
      f.write(self._makeLogLine(future))
      path = f.name
    try:
      status, message = software.check_cdn_node_activity_check(path)
      self.assertEqual(status, 'warning')
      self.assertIn('future', message)
    finally:
      os.unlink(path)

  def test_custom_max_age(self):
    now = datetime.now()
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log',
                                     delete=False) as f:
      # 30 seconds old: within default 300s but outside custom 10s
      f.write(self._makeLogLine(now - timedelta(seconds=30)))
      path = f.name
    try:
      status, message = software.check_cdn_node_activity_check(
        path, max_age_seconds=10)
      self.assertEqual(status, 'error')
      self.assertIn('no recent activity', message)

      status, message = software.check_cdn_node_activity_check(
        path, max_age_seconds=60)
      self.assertEqual(status, 'ok')
    finally:
      os.unlink(path)

  def test_multiple_lines_uses_last(self):
    now = datetime.now()
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log',
                                     delete=False) as f:
      # Old line followed by recent line
      f.write(self._makeLogLine(now - timedelta(hours=1)))
      f.write(self._makeLogLine(now - timedelta(seconds=5)))
      path = f.name
    try:
      status, message = software.check_cdn_node_activity_check(path)
      self.assertEqual(status, 'ok')
    finally:
      os.unlink(path)
