# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010, 2011, 2012 Vifib SARL and Contributors.
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

import os
import sys
import argparse
import logging
import logging.handlers
import ConfigParser


class ProxyConfig(object):
  def setConfig(self, option_dict, configuration_file_path):
    """
    Set options given by parameters.
    """
    # Set options parameters
    for option, value in option_dict.__dict__.items():
      setattr(self, option, value)

    # Load configuration file
    configuration_parser = ConfigParser.SafeConfigParser()
    configuration_parser.read(configuration_file_path)
    # Merges the arguments and configuration
    for section in ("slapproxy", "slapos"):
      configuration_dict = dict(configuration_parser.items(section))
      for key in configuration_dict:
        if not getattr(self, key, None):
          setattr(self, key, configuration_dict[key])

    # set up logging
    self.logger = logging.getLogger("slapproxy")
    self.logger.setLevel(logging.INFO)
    self.logger.addHandler(logging.StreamHandler())

    if not self.database_uri:
      raise ValueError('database-uri is required.')
    if self.log_file:
      if not os.path.isdir(os.path.dirname(self.log_file)):
        raise ValueError('Please create directory %r to store %r log file' % (
          os.path.dirname(self.log_file), self.log_file))
      else:
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        self.logger.addHandler(file_handler)
        self.logger.info('Configured logging to file %r' % self.log_file)

    if self.verbose:
      self.logger.setLevel(logging.DEBUG)



def run(config):
  from views import app
  app.config['computer_id'] = config.computer_id
  app.config['DATABASE_URI'] = config.database_uri
  app.run(host=config.host, port=int(config.port))


def main():
  ap = argparse.ArgumentParser()

  ap.add_argument('-l', '--log_file',
                  help='The path to the log file used by the script.')

  ap.add_argument('-v', '--verbose',
                  action='store_true',
                  help='Verbose output.')

  # XXX not used anymore, deprecated
  ap.add_argument('-c', '--console',
                  action='store_true',
                  help='Console output.')

  ap.add_argument('-u', '--database-uri',
                  help='URI for sqlite database')

  ap.add_argument('configuration_file',
                  help='path to slapos.cfg')

  args = ap.parse_args()

  try:
    conf = ProxyConfig()
    conf.setConfig(args, args.configuration_file)
    run(conf)
    return_code = 0
  except SystemExit as err:
    return_code = err

  sys.exit(return_code)
