# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010-2014 Vifib SARL and Contributors.
# All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import logging
import sys

from slapos.cli.config import ClientConfigCommand
from slapos.client import init, ClientConfig

def resetLogger(logger):
    """Remove all formatters, log files, etc."""
    if not getattr(logger, 'parent', None):
      return
    handler = logger.parent.handlers[0]
    logger.parent.removeHandler(handler)
    logger.addHandler(logging.StreamHandler(sys.stdout))

class ListCommand(ClientConfigCommand):
    """request an instance and get status and parameters of instance"""

    def get_parser(self, prog_name):
        ap = super(ListCommand, self).get_parser(prog_name)
        return ap

    def take_action(self, args):
        configp = self.fetch_config(args)
        conf = ClientConfig(args, configp)

        local = init(conf, self.app.log)
        do_list(self.app.log, conf, local)


def do_list(logger, conf, local):
    resetLogger(logger)
    # XXX catch exception
    instance_dict = local['slap'].getOpenOrderDict()
    if instance_dict == {}:
      logger.info('No existing service.')
      return
    logger.info('List of services:')
    for title, instance in instance_dict.iteritems():
      logger.info('%s %s', title, instance._software_release_url)
