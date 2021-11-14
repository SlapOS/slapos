##############################################################################
# coding: utf-8
# Copyright (c) 2021 Nexedi SA and Contributors. All Rights Reserved.
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

import functools
import os
import lzma
import multiprocessing
import urllib.parse

import uritemplate
import requests

from slapos.testing.utils import CrontabMixin
from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class TestNginxPushStream(SlapOSInstanceTestCase, CrontabMixin):
  def setUp(self):
    self.connection_parameters = \
        self.computer_partition.getConnectionParameterDict()

  def test_push_stream_scenario(self):
    def process_messages(q):
      # type:(multiprocessing.Queue[bytes]) -> None
      req = requests.get(
          uritemplate.URITemplate(
              self.connection_parameters['subscriber-url']).expand(
                  id='channel_id'),
          verify=False,
          stream=True,
      )
      if not req.ok:
        q.put(('error: wrong status code %s' % req.status_code).encode())
      q.put(b'ready')
      for _, line in zip(range(2), req.iter_lines()):
        q.put(line)

    q = multiprocessing.Queue()  # type: multiprocessing.Queue[bytes]
    subscriber = multiprocessing.Process(target=process_messages, args=(q, ))
    subscriber.start()
    self.assertEqual(q.get(timeout=30), b'ready')

    resp = requests.post(
        uritemplate.URITemplate(
            self.connection_parameters['publisher-url']).expand(
                id='channel_id'),
        verify=False,
        data='Hello',
        timeout=2,
    )
    resp.raise_for_status()

    try:
      subscriber.join(timeout=30)
    except multiprocessing.TimeoutError:
      subscriber.terminate()
      subscriber.join(timeout=30)
      self.fail('Process did not terminate')

    self.assertEqual(q.get_nowait(), b': ')
    self.assertEqual(q.get_nowait(), b'data: Hello')

  def test_log_rotation(self):
    status_url = urllib.parse.urljoin(
        self.connection_parameters['publisher-url'], '/status')
    error_url = urllib.parse.urljoin(
        self.connection_parameters['publisher-url'], '/..')
    log_file_path = functools.partial(
        os.path.join,
        self.computer_partition_root_path,
        'var',
        'log',
    )
    rotated_file_path = functools.partial(
        os.path.join,
        self.computer_partition_root_path,
        'srv',
        'backup',
        'logrotate',
    )

    requests.get(status_url, verify=False)
    with open(log_file_path('nginx-access.log')) as f:
      self.assertIn('GET /status HTTP', f.read())
    requests.get(error_url, verify=False)
    with open(log_file_path('nginx-error.log')) as f:
      self.assertIn('forbidden', f.read())

    # first log rotation initialize the state, but does not actually rotate
    self._executeCrontabAtDate('logrotate', '2050-01-01')
    self._executeCrontabAtDate('logrotate', '2050-01-02')

    # today's file is not compressed
    with open(rotated_file_path('nginx-access.log-20500102')) as f:
      self.assertIn('GET /status HTTP', f.read())
    with open(rotated_file_path('nginx-error.log-20500102')) as f:
      self.assertIn('forbidden', f.read())

    # after rotation, the program re-opened original log file and writes in
    # expected location.
    requests.get(status_url, verify=False)
    with open(log_file_path('nginx-access.log')) as f:
      self.assertIn('GET /status HTTP', f.read())
    requests.get(error_url, verify=False)
    with open(log_file_path('nginx-error.log')) as f:
      self.assertIn('forbidden', f.read())

    self._executeCrontabAtDate('logrotate', '2050-01-03')
    # yesterday's file are compressed
    with lzma.open(rotated_file_path('nginx-access.log-20500102.xz'), 'rt') as f:
      self.assertIn('GET /status HTTP', f.read())
    with lzma.open(rotated_file_path('nginx-error.log-20500102.xz'), 'rt') as f:
      self.assertIn('forbidden', f.read())
