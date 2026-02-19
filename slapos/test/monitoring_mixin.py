##############################################################################
#
# Copyright (c) 2026 Nexedi SA and Contributors. All Rights Reserved.
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

from six.moves.urllib.parse import urlparse

class MonitoringPropagationTestMixin(object):
  """Verify that monitor-interface-url propagates correctly to all partitions."""

  # A recognisable URL with a domain that cannot appear in default configs.
  MONITOR_CORS_DOMAIN = 'monitor.propagation.test'
  MONITOR_INTERFACE_URL = (
      'https://' + MONITOR_CORS_DOMAIN + '/#page=ojsm_landing')

  @classmethod
  def getInstanceParameterDict(cls):
    return {'monitor-interface-url': cls.MONITOR_INTERFACE_URL}

  def test_monitor_interface_url_propagation(self):
    """All monitored partitions carry the expected monitor-interface-url.

    For single-partition SRs only the root partition is checked.  For
    multi-partition SRs the root forwards ``config-monitor-interface-url`` to
    each child, so every child partition should also carry the value.
    """
    monitored_partition_ids = []
    for partition in self.slap.computer.getComputerPartitionList():
      if partition.getState() == 'destroyed':
        continue
      params = partition.getInstanceParameterDict()
      if 'monitor-interface-url' not in params:
        continue
      monitored_partition_ids.append(partition.getId())
      self.assertEqual(
        params['monitor-interface-url'],
        self.MONITOR_INTERFACE_URL,
        'Partition {!r} has wrong monitor-interface-url'.format(
            partition.getId()),
      )

    self.assertGreater(
      len(monitored_partition_ids),
      0,
      msg='No partition received monitor-interface-url',
    )

  def test_monitor_setup_url_contains_interface_url(self):
    """monitor-setup-url in connection params embeds monitor-interface-url."""

    setup_url_list = [
      partition.getConnectionParameterDict().get('monitor-setup-url')
      for partition in self.slap.computer.getComputerPartitionList()
      if partition.getState() != 'destroyed'
    ]
    setup_url_list = [u for u in setup_url_list if u is not None]

    self.assertGreater(
      len(setup_url_list),
      0,
      msg='No partition published monitor-setup-url',
    )
    for setup_url in setup_url_list:
      self.assertIn(
        self.MONITOR_INTERFACE_URL,
        setup_url,
        'monitor-setup-url does not embed monitor-interface-url',
      )