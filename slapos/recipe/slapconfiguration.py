##############################################################################
#
# Copyright (c) 2012 Vifib SARL and Contributors. All Rights Reserved.
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
import slapos.slap
from ConfigParser import RawConfigParser

class Recipe(object):
  """
  Retrieves slap partition parameters, and makes them available to other
  buildout section in various ways, and in various encodings.
  Populates the buildout section it is used in with all slap partition
  parameters.

  Input:
    url
      Slap server url.
      Example:
        ${slap-connection:server-url}
    key & cert (optional)
      Path of files containing key and certificate for secure connection to
      slap server.
      Example:
        ${slap-connection:key-file}
        ${slap-connection:cert-file}
    computer
      Computer identifier.
      Example:
        ${slap-connection:computer-id}
    partition
      Partition identifier.
      Example:
        ${slap-connection:partition-id}

  Output:
    slap-software-type
      Current partition's software type.
    configuration
      Dict of all parameters.
    configuration.<key>
      One key per partition parameter.
      Partition parameter whose name cannot be represented unambiguously in
      buildout syntax are ignored. They cannot be accessed from buildout syntax
      anyway, and are available through "configuration" output key.
  """

  # XXX: used to detect if a configuration key is a valid section key. This
  # assumes buildout uses ConfigParser - which is currently the case.
  OPTCRE_match = RawConfigParser.OPTCRE.match

  def __init__(self, buildout, name, options):
      slap = slapos.slap.slap()
      slap.initializeConnection(
          options['url'],
          options.get('key'),
          options.get('cert'),
      )
      parameter_dict = slap.registerComputerPartition(
          options['computer'],
          options['partition'],
      ).getInstanceParameterDict()
      # XXX: those are not partition parameters, strictly speaking.
      # Discard them, and make them available as separate section keys.
      options['slap-software-type'] = parameter_dict.pop(
          'slap_software_type')
      del parameter_dict['ip_list']
      options['configuration'] = parameter_dict
      match = self.OPTCRE_match
      for key, value in parameter_dict.iteritems():
          if match(key) is not None:
              continue
          options['configuration.' + key] = value

  install = update = lambda self: []
