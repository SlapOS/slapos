# -*- coding: utf-8 -*-
# vim: set et sts=2:
##############################################################################
#
# Copyright (c) 2011, 2012 Vifib SARL and Contributors.
# All Rights Reserved.
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

import slapos.slap.slap


def do_bang(configp, message):
  computer_id = configp.get('slapos', 'computer_id')
  master_url = configp.get('slapos', 'master_url')
  if configp.has_option('slapos', 'key_file'):
    key_file = configp.get('slapos', 'key_file')
  else:
    key_file = None
  if configp.has_option('slapos', 'cert_file'):
    cert_file = configp.get('slapos', 'cert_file')
  else:
    cert_file = None
  slap = slapos.slap.slap()
  slap.initializeConnection(master_url, key_file=key_file, cert_file=cert_file)
  computer = slap.registerComputer(computer_id)
  print 'Banging to %r' % master_url
  computer.bang(message)
  print 'Bang with message %r' % message
