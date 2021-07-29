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

import os
import multiprocessing

import requests

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class TestNginxPushStream(SlapOSInstanceTestCase):
  def setUp(self):
    self.connection_parameters = \
        self.computer_partition.getConnectionParameterDict()

  def test_push_stream_scenario(self):
    def process_messages(q):
      # type:(multiprocessing.Queue[bytes]) -> None
      req = requests.get(
          self.connection_parameters['subscriber-url'] + '/channel_id',
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
        self.connection_parameters['publisher-url'] + '?id=channel_id',
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
