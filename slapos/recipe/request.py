##############################################################################
#
# Copyright (c) 2010 Vifib SARL and Contributors. All Rights Reserved.
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
import logging
import os

from slapos import slap as slapmodule

class Recipe(object):

  def parseMultiValues(self, string):
    return dict([ [str(column).strip() for column in line.split('=', 1)]
                 for line in str(string).splitlines() if '=' in line])

  def __init__(self, buildout, name, options):
    self.logger = logging.getLogger(name)

    slap = slapmodule.slap()

    self.software_release_url = options['software-url']

    slap.initializeConnection(options['server-url'],
                              options.get('key-file'),
                              options.get('cert-file'),
                             )
    computer_partition = slap.registerComputerPartition(
      options['computer-id'], options['partition-id'])
    self.request = computer_partition.request

    if 'name' not in options:
      options['name'] = name

    self.return_parameters = []
    if 'return' in options:
      self.return_parameters = [str(parameter).strip()
                               for parameter in options['return'].split()]
    else:
      self.logger.warning("No parameter to return to main instance."
                          "Be careful about that...")

    software_type = 'RootInstanceSoftware'
    if 'software-type' in options:
      software_type = options['software-type']

    filter_kw = {}
    if 'sla' in options:
      filter_kw = self.parseMultiValues(options['sla'])

    partition_parameter_kw = {}
    if 'config' in options:
      partition_parameter_kw = self.parseMultiValues(options['config'])

    instance = self.request(options['software-url'], software_type,
      options['name'], partition_parameter_kw=partition_parameter_kw,
        filter_kw=filter_kw)

    result = {}
    for param in self.return_parameters:
      try:
        result[param] = instance.getConnectionParameter(param)
      except slapmodule.NotFoundError:
        result[param] = None

    # Return the connections parameters in options dict
    for key, value in result.items():
      options['connection-%s' % key] = value

  def install(self):
    return []

  update = install
