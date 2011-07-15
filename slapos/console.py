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
from slapos.slap import ResourceNotReady

import sys
import os
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
    if len(args) == 0:
      self.error("Incorrect number of arguments")
    elif not os.path.isfile(args[0]):
      self.error("%s: Not found or not a regular file." % args[0])

    return options, args

class RequestParser(Parser):
  def check_args(self):
    """
    Check arguments
    """
    (options, args) = Parser.check_args(self)
    if len(args) < 3:
      self.error("Incorrect number of arguments")

    return options, args

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
    try:
      configuration_dict = dict(configuration_parser.items("slapconsole"))
    except ConfigParser.NoSectionError:
      pass
    else:
      for key in configuration_dict:
        if not getattr(self, key, None):
          setattr(self, key, configuration_dict[key])
    configuration_dict = dict(configuration_parser.items('slapos'))
    master_url = configuration_dict.get('master_url', None)
    if not master_url:
      raise ValueError("No option 'master_url'")
    elif master_url.startswith('https') and \
         not getattr(self, 'key_file', None) and \
         not getattr(self, 'cert_file', None):
      raise ValueError("No option 'key_file' and/or 'cert_file'")
    else:
      setattr(self, 'master_url', master_url)

def init(config):
  """Initialize Slap instance, connect to server and create
  aliases to common software releases"""
  slap = slapos.slap.slap()
  slap.initializeConnection(config.master_url,
      key_file=config.key_file, cert_file=config.cert_file)
  local = globals().copy()
  local['slap'] = slap
  # Create aliases as global variables
  try:
    alias = config.alias.split('\n')
  except AttributeError:
    alias = []
  software_list = []
  for software in alias:
    if software is not '':
      name, url = software.split(' ')
      software_list.append(name)
      local[name] = url
  # Create global variable too see available aliases
  local['software_list'] = software_list
  # Create global shortcut functions to request instance and software
  # XXX-Cedric : can we change given parameters to something like
  # *args, **kwargs, but without the bad parts, in order to be generic?
  def shorthandRequest(software_release, partition_reference,
      partition_parameter_kw=None, software_type=None, filter_kw=None,
      state=None):
    return slap.registerOpenOrder().request(software_release, partition_reference,
      partition_parameter_kw, software_type, filter_kw, state)
  def shorthandSupply(software_release, computer_guid=None):
    return slap.registerSupply().supply(software_release, computer_guid)
  local['request'] = shorthandRequest
  local['supply'] = shorthandSupply

  return local

def request():
  """Ran when invoking slapos-request"""
  # Parse arguments
  usage = """usage: %s [options] CONFIGURATION_FILE SOFTWARE_INSTANCE INSTANCE_REFERENCE
slapos-request allows you to request slapos instances.""" % sys.argv[0]
  config = Config()
  options, arguments = RequestParser(usage=usage).check_args()
  config.setConfig(options, arguments[0])
  
  local = init(config)
  
  # Request instance
  # XXX-Cedric : support things like : 
  # --instance-type std --configuration-size 23 --computer-region europe/france
  # XXX-Cedric : add support for xml_parameter
  software_url = arguments[1]
  partition_reference = arguments[2]
  print("Requesting %s..." % software_url)
  if software_url in local:
    software_url = local[software_url]
  try:
    partition = local['slap'].registerOpenOrder().request(software_url,
        partition_reference)
    print("Instance requested.\nState is : %s.\nYou can "
        "rerun to get up-to-date informations." % (
        partition.getState()))
    # XXX-Cedric : provide a way for user to fetch parameter, url, object, etc
  except ResourceNotReady:
    print("Instance requested. Master is provisionning it. Please rerun in a "
    "couple of minutes to get connection informations")
    exit(2)

def run():
  """Ran when invoking slapconsole"""
  # Parse arguments
  usage = """usage: %s [options] CONFIGURATION_FILE
slapconsole allows you interact with slap API. You can play with the global
"slap" object and with the global "request" method.

examples :
  >>> # Request instance
  >>> request(kvm, "myuniquekvm")
  >>> # Request software installation on owned computer
  >>> supply(kvm, "mycomputer")
  >>> # Fetch instance informations on already launched instance
  >>> request(kvm, "myuniquekvm").getConnectionParameter("url")""" % sys.argv[0]
  config = Config()
  config.setConfig(*Parser(usage=usage).check_args())
  
  local = init(config)
  __import__("code").interact(banner="", local=local)
