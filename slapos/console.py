##############################################################################
#
# Copyright (c) 2010 Vifib SARL and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
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

import slapos.slap.slap

import sys
from optparse import OptionParser, Option
import ConfigParser

class Parser(OptionParser):
  """
  Parse all arguments.
  """
  def __init__(self, usage=None, version=None):
    """
    Initialize all options possibles.
    """
    OptionParser.__init__(self, usage=usage, version=version,
                          option_list=[
        Option("-u", "--master_url",
               default=None,
               action="store",
               help="Url of SlapOS Master to use."),
        Option("-k", "--key_file",
              action="store",
              help="SSL Authorisation key file."),
        Option("-c", "--cert_file",
            action="store",
            help="SSL Authorisation certificate file.")
    ])

  def check_args(self):
    """
    Check arguments
    """
    (options, args) = self.parse_args()
    if len(args) != 1:
      self.error("Incorrect number of arguments")

    return options, args[0]

class Config:
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
    for section in ("slapos",):
      configuration_dict = dict(configuration_parser.items(section))
      for key in configuration_dict:
        if not getattr(self, key, None):
          setattr(self, key, configuration_dict[key])
          
    if not self.master_url:
      raise ValueError('master-url is required.')
  
def run():
  usage = "usage: %s [options] CONFIGURATION_FILE" % sys.argv[0]
  # Parse arguments
  config = Config()
  config.setConfig(*Parser(usage=usage).check_args())
  
  slap = slapos.slap.slap()
  slap.initializeConnection('https://slap.vifib.com',
      key_file=config.key_file, cert_file=config.cert_file)
  local = globals()
  local['slap'] = slap
  # XXX-Cedric Maybe we should generate a new OpenOrder for each request?
  local['request'] = slap.registerOpenOrder().request
  
  __import__("code").interact(banner="", local=globals())
