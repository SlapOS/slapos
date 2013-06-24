# -*- coding: utf-8 -*-

import ConfigParser
import os

from slapos.cli.command import Command


class ConfigError(Exception):
    pass


class ConfigCommand(Command):
    "Base class for commands that require a configuration file"

    log = None

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

        self.log.debug('Loading config: %s', cfg_path)

        if not os.path.exists(cfg_path):
            raise ConfigError('Configuration file does not exist: %s' % cfg_path)

        configp = ConfigParser.SafeConfigParser()
        if configp.read(cfg_path) != [cfg_path]:
            # bad permission, etc.
            raise ConfigError('Cannot parse configuration file: %s' % cfg_path)

        return configp


class ClientConfigCommand(ConfigCommand):
    default_config_var = 'SLAPOS_CLIENT_CONFIGURATION'
    default_config_path = '~/.slapos/slapos-client.cfg'
