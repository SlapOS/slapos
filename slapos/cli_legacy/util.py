# -*- coding: utf-8 -*-

import ConfigParser
import os


def get_config_parser(path):
    configuration_parser = ConfigParser.SafeConfigParser()
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        raise OSError('Specified configuration file %s does not exist. Exiting.' % path)
    configuration_parser.read(path)
    return configuration_parser


