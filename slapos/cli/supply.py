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

from slapos.cli.config import ClientConfigCommand
from slapos.client import init, ClientConfig, _getSoftwareReleaseFromSoftwareString

class SupplyCommand(ClientConfigCommand):
    """
    supply a Software to a node
    """

    def get_parser(self, prog_name):
        ap = super(SupplyCommand, self).get_parser(prog_name)

        ap.add_argument('software_url',
                        help='Your software url')

        ap.add_argument('node',
                        help='Target node')

        return ap

    def take_action(self, args):
        configp = self.fetch_config(args)
        conf = ClientConfig(args, configp)
        local = init(conf, self.app.log)
        do_supply(self.app.log, args.software_url, args.node, local)


def do_supply(logger, software_release, computer_id, local):
    """
    Request installation of Software Release
    'software_release' on computer 'computer_id'.
    """
    logger.info('Requesting software installation of %s...',
                software_release)

    software_release = _getSoftwareReleaseFromSoftwareString(
        logger, software_release, local['product'])

    local['supply'](
        software_release=software_release,
        computer_guid=computer_id,
        state='available'
    )
    logger.info('Done.')
