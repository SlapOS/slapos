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
import pprint
import sys

from slapos.cli.config import ClientConfigCommand
from slapos.client import init, ClientConfig
from slapos.slap import ResourceNotReady, NotFoundError


def resetLogger(logger):
    """Remove all formatters, log files, etc."""
    if not getattr(logger, 'parent', None):
      return
    handler = logger.parent.handlers[0]
    logger.parent.removeHandler(handler)
    logger.addHandler(logging.StreamHandler(sys.stdout))

class InfoCommand(ClientConfigCommand):
    """get status, software_release and parameters of an instance"""

    def get_parser(self, prog_name):
        ap = super(InfoCommand, self).get_parser(prog_name)

        ap.add_argument('reference',
                        help='Your instance reference')

        return ap

    def take_action(self, args):
        configp = self.fetch_config(args)
        conf = ClientConfig(args, configp)

        local = init(conf, self.app.log)
        exit_code = do_info(self.app.log, conf, local)
        if exit_code != 0:
          exit(exit_code)


def do_info(logger, conf, local):
    resetLogger(logger)
    try:
        instance = local['slap'].registerOpenOrder().getInformation(
            partition_reference=conf.reference,
        )
    except ResourceNotReady:
        logger.warning('Instance does not exist or is not ready yet.')
        return(2)
    except NotFoundError:
        logger.warning('Instance %s does not exist.', conf.reference)
        return(2)

    logger.info('Software Release URL: %s', instance._software_release_url)
    logger.info('Instance state: %s', instance._requested_state)
    logger.info('Instance parameters:')
    logger.info(pprint.pformat(instance._parameter_dict))
    logger.info('Connection parameters:')
    logger.info(pprint.pformat(instance._connection_dict))

