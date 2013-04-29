# -*- coding: utf-8 -*-
# vim: set et sts=2:
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

import argparse
import logging
import sys

from slapos.register.register import do_register, RegisterConfig


def main():
  ap = argparse.ArgumentParser(usage='usage: slapos node %s NODE_NAME [options]' % sys.argv[0])

  ap.add_argument('node_name',
                  help='Name of the node')

  ap.add_argument('--interface-name',
                  help='Interface name to access internet',
                  default='eth0')

  ap.add_argument('--master-url',
                  help='URL of SlapOS master',
                  default='https://slap.vifib.com')

  ap.add_argument('--master-url-web',
                  help='URL of SlapOS Master webservice to register certificates',
                  default='https://www.slapos.org')

  ap.add_argument('--partition-number',
                  help='Number of partition on computer',
                  default='10',
                  type=int)

  ap.add_argument('--ipv4-local-network',
                  help='Base of ipv4 local network',
                  default='10.0.0.0/16')

  ap.add_argument('--ipv6-interface',
                  help='Interface name to get ipv6',
                  default='')

  ap.add_argument('--login',
                  help='User login on SlapOS Master webservice')

  ap.add_argument('--password',
                  help='User password on SlapOs Master webservice')

  ap.add_argument('-t', '--create-tap',
                  help='Will trigger creation of one virtual "tap" interface per '
                       'Partition and attach it to primary interface. Requires '
                       'primary interface to be a bridge. defaults to false. '
                       'Needed to host virtual machines.',
                  default=False,
                  action='store_true')

  ap.add_argument('-n', '--dry-run',
                  help='Simulate the execution steps',
                  default=False,
                  action='store_true')

  args = ap.parse_args()

  if args.password and not args.login:
    ap.error('Please enter your login with your password')

  logger = logging.getLogger('Register')
  handler = logging.StreamHandler()
  logger.setLevel(logging.DEBUG)
  handler.setLevel(logging.INFO)
  handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
  logger.addHandler(handler)

  try:
    conf = RegisterConfig(logger=logger)
    conf.setConfig(args)
    return_code = do_register(conf)
  except SystemExit as exc:
    # Catch exception raised by optparse
    # XXX returning exception with sys.exit?
    return_code = exc

  sys.exit(return_code)
