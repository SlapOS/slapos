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

import ConfigParser
import os

from slapos.cli.command import Command


class ConfigError(Exception):
    pass


class ConfigCommand(Command):
    """
    Base class for commands that require a configuration file
    """

    default_config_var = 'SLAPOS_CONFIGURATION'

    # use this if default_config_var does not exist
    default_config_path = '/etc/opt/slapos/slapos.cfg'

    def get_parser(self, prog_name):
        ap = super(ConfigCommand, self).get_parser(prog_name)
        ap.add_argument('--cfg',
                        help='SlapOS configuration file'
                             ' (default: $%s or %s)' %
                             (self.default_config_var, self.default_config_path))
        return ap

    def config_path(self, args):
        if args.cfg:
            cfg_path = args.cfg
        else:
            cfg_path = os.environ.get(self.default_config_var, self.default_config_path)
        return os.path.expanduser(cfg_path)

    def fetch_config(self, args):
        """
        Returns a configuration object if file exists/readable/valid,
        will raise an error otherwise. The exception may come from the
        configparser itself if the configuration content is very broken,
        and will clearly show what is wrong with the file.
        """

        cfg_path = self.config_path(args)

        self.app.log.debug('Loading config: %s', cfg_path)

        if not os.path.exists(cfg_path):
            raise ConfigError('Configuration file does not exist: %s' % cfg_path)

        configp = ConfigParser.SafeConfigParser()
        if configp.read(cfg_path) != [cfg_path]:
            # bad permission, etc.
            raise ConfigError('Cannot parse configuration file: %s' % cfg_path)

        return configp


class ClientConfigCommand(ConfigCommand):
    """
    Base class for client commands, that use the client configuration file
    """

    default_config_var = 'SLAPOS_CLIENT_CONFIGURATION'
    default_config_path = '~/.slapos/slapos-client.cfg'
    command_group = 'client'
