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

from slapos.cli.config import ConfigCommand
from slapos.proxy import do_proxy, ProxyConfig


class ProxyStartCommand(ConfigCommand):
    """
    minimalist, stand-alone SlapOS Master
    """

    def get_parser(self, prog_name):
        ap = super(ProxyStartCommand, self).get_parser(prog_name)

        ap.add_argument('-u', '--database-uri',
                        help='URI for sqlite database')
        ap.add_argument('--port',
                        help='Port to use')
        ap.add_argument('--host',
                        help='Host to use')

        return ap

    def take_action(self, args):
        configp = self.fetch_config(args)

        conf = ProxyConfig(logger=self.app.log)

        conf.mergeConfig(args, configp)

        if not self.app.options.log_file and hasattr(conf, 'log_file'):
            # no log file is provided by argparser,
            # we set up the one from config
            file_handler = logging.FileHandler(conf.log_file)
            formatter = logging.Formatter(self.app.LOG_FILE_MESSAGE_FORMAT)
            file_handler.setFormatter(formatter)
            self.app.log.addHandler(file_handler)

        conf.setConfig()

        do_proxy(conf=conf)
