# -*- coding: utf-8 -*-

import ConfigParser
import os


def get_config_parser(path):
    configp = ConfigParser.SafeConfigParser()
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        raise OSError('Specified configuration file %s does not exist. Exiting.' % path)
    configp.read(path)
    return configp
