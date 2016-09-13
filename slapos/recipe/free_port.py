##############################################################################
#
# Copyright (c) 2016 Vifib SARL and Contributors. All Rights Reserved.
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

import ConfigParser
import os
import netaddr
import socket

class Recipe(object):
  """
  Uses the socket python standard library to get an unused port.

  Notice : this recipe may still fail because of race condition : if a new
  process spawns and use the picked port before the service for which it has
  been generated starts, then the service won't start. Therefore, the result
  would be the same giving an already-in-use port to the service.
  """

  def __init__(self, buildout, name, options):
    self.options = options

    # If section has already been installed, port is already taken by the
    # requested service itself.
    # If this check isn't done, a new port would be picked for every upgrade
    # of the software release
    try:
      parser = ConfigParser.RawConfigParser()
      if os.path.exists(buildout['buildout']['installed']):
        with open(buildout['buildout']['installed']) as config_file:
          parser.readfp(config_file)
        port = parser.get(name, 'port')
        # Port can be 0 in case of upgrade: some old service still runs on port,
        # so 0 is returned by default. Then, on next run, this recipe is processed
        # again until a correct value is returned
        if port != '0':
          self.options['port'] = port
          return
    except (IOError, ConfigParser.NoSectionError, ConfigParser.NoOptionError):
      pass

    # Otherwise, let's find one
    self.minimum = int(options.get('minimum', 1024))
    self.maximum = int(options.get('maximum', 49151))
    self.ip = options.get('ip')

    if self.minimum == self.maximum:
      self.options['port'] = str(self.minimum)
      return

    if netaddr.valid_ipv4(self.ip):
      self.inet_family = socket.AF_INET
    elif netaddr.valid_ipv6(self.ip):
      self.inet_family = socket.AF_INET6
    else:
      # address family is unknown, so let's return a general purpose port
      self.options['port'] = str(0)
      return

    self.options['port'] = str(self._getFreePort())

  def _getFreePort(self):
    """
    Port number will be picked from a given range, smaller port first, then
    incremented until a free one is found.
    This algorithm thus returns always the same value with the same parameters in
    a standard environment.
    """
    for port in xrange(self.minimum, self.maximum):
      sock = socket.socket(self.inet_family, socket.SOCK_STREAM)
      try:
        sock.bind((self.ip, port))
        break
      except socket.error:
        continue
      finally:
        sock.close()
    else:
      port = 0

    return port

  install = update = lambda self: []
