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

import argparse
import ConfigParser
import pprint
from optparse import OptionParser, Option
import os
from slapos.slap import ResourceNotReady
import slapos.slap.slap
import sys
import atexit

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

    # Return options and only first element of args since there is only one.
    return options, args[0]


def argToDict(element):
  """
  convert a table of string 'key=value' to dict
  """
  if element is not None:
    element_dict = dict([arg.split('=') for arg in element])
  return element_dict

def check_request_args():
  """
  Parser for request
  """
  parser = argparse.ArgumentParser()
  parser.add_argument("configuration_file",
                      help="SlapOS configuration file.")
  parser.add_argument("reference",
                      help="Your instance reference")
  parser.add_argument("software_url",
                      help="Your software url")
  parser.add_argument("--node",
                      nargs = '*',
                      help = "Node request option "
                      "'option1=value1 option2=value2'")
  parser.add_argument("--type",
                      type = str,
                      help = "Define software type to be requested")
  parser.add_argument("--slave",
                      action = "store_true", default=False,
                      help = "Ask for a slave instance")
  parser.add_argument("--configuration",
                      nargs = '*',
                      help = "Give your configuration "
                      "'option1=value1 option2=value2'")
  args = parser.parse_args()
  # Convert to dict
  if args.configuration is not None:
    args.configuration = argToDict(args.configuration)
  if args.node is not None:
    args.node = argToDict(args.node)
  return args


class Config:
  def __init__(self, option_dict, configuration_file_path=None):
    """
    Set options given by parameters.
    """
    # Set options parameters
    for option, value in option_dict.__dict__.items():
      setattr(self, option, value)

    # Load configuration file
    configuration_parser = ConfigParser.SafeConfigParser()
    if configuration_file_path:
      configuration_file_path = os.path.expanduser(configuration_file_path)
      if not os.path.isfile(configuration_file_path):
        raise OSError('Specified configuration file %s does not exist.'
            ' Exiting.' % configuration_file_path)
      configuration_parser.read(configuration_file_path)
    # Merges the arguments and configuration
    try:
      configuration_dict = dict(configuration_parser.items('slapconsole'))
    except ConfigParser.NoSectionError:
      pass
    else:
      for key in configuration_dict:
        if not getattr(self, key, None):
          setattr(self, key, configuration_dict[key])
    configuration_dict = dict(configuration_parser.items('slapos'))
    master_url = configuration_dict.get('master_url', None)
    # Backward compatibility, if no key and certificate given in option
    # take one from slapos configuration
    if not getattr(self, 'key_file', None) and \
          not getattr(self, 'cert_file', None):
      self.key_file = configuration_dict.get('key_file')
      self.cert_file = configuration_dict.get('cert_file')
    if not master_url:
      raise ValueError("No option 'master_url'")
    elif master_url.startswith('https') and \
         self.key_file is None and \
         self.cert_file is None:
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
  def shorthandRequest(*args, **kwargs):
    return slap.registerOpenOrder().request(*args, **kwargs)
  def shorthandSupply(*args, **kwargs):
    return slap.registerSupply().supply(*args, **kwargs)
  local['request'] = shorthandRequest
  local['supply'] = shorthandSupply

  return local

def request():
  """Run when invoking slapos request. Request an instance."""
  # Parse arguments and inititate needed parameters
  # XXX-Cedric: move argument parsing to main entry point
  options = check_request_args()
  config = Config(options, options.configuration_file)
  local = init(config)
  # Request instance
  print("Requesting %s..." % config.reference)
  if config.software_url in local:
    config.software_url = local[config.software_url]
  try:
    partition = local['slap'].registerOpenOrder().request(
      software_release = config.software_url,
      partition_reference = config.reference,
      partition_parameter_kw = config.configuration,
      software_type = config.type,
      filter_kw = config.node,
      shared = config.slave
    )
    print "Instance requested.\nState is : %s." % partition.getState()
    print "Connection parameters of instance are:"
    pprint.pprint(partition.getConnectionParameterDict())
    print "You can rerun command to get up-to-date informations."
  except ResourceNotReady:
    print("Instance requested. Master is provisionning it. Please rerun in a "
        "couple of minutes to get connection informations.")
    exit(2)

def _supply(software_url, computer_id, local, remove=False):
  """
  Request installation of Software Release
  'software_url' on computer 'computer_id'.
  if destroy argument is True, request deletion of Software Release.
  """
  # XXX-Cedric Implement software_group support
  # XXX-Cedric Implement computer_group support
  if not remove:
    state = 'available'
    print 'Requesting installation of %s Software Release...' % software_url

  else:
    state = 'destroyed'
    print 'Requesting deletion of %s Software Release...' % software_url

  if software_url in local:
    software_url = local[software_url]
  local['slap'].registerSupply().supply(
      software_release=software_url,
      computer_guid=computer_id,
      state=state,
  )
  print 'Done.'

def supply():
  """
  Run when invoking slapos supply. Mostly argument parsing.
  """
  # XXX-Cedric: move argument parsing to main entry point
  parser = argparse.ArgumentParser()
  parser.add_argument("configuration_file",
                      help="SlapOS configuration file")
  parser.add_argument("software_url",
                      help="Your software url")
  parser.add_argument("node",
                      help="Target node")
  args = parser.parse_args()

  config = Config(args, args.configuration_file)
  _supply(args.software_url, args.node, init(config))

def remove():
  """
  Run when invoking slapos remove. Mostly argument parsing.
  """
  # XXX-Cedric: move argument parsing to main entry point
  parser = argparse.ArgumentParser()
  parser.add_argument("configuration_file",
                      help="SlapOS configuration file.")
  parser.add_argument("software_url",
                      help="Your software url")
  parser.add_argument("node",
                      help="Target node")
  args = parser.parse_args()

  config = Config(args, args.configuration_file)
  _supply(args.software_url, args.node, init(config), remove=True)


def slapconsole():
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
  config = Config(*Parser(usage=usage).check_args())
  local = init(config)

  # try to enable readline with completion and history
  try:
    import readline
  except ImportError:
    pass
  else:
    try:
      import rlcompleter
      readline.set_completer(rlcompleter.Completer(local).complete)
    except ImportError:
      pass
    readline.parse_and_bind("tab: complete")

    historyPath = os.path.expanduser("~/.slapconsolehistory")
    def save_history(historyPath=historyPath):
      readline.write_history_file(historyPath)
    if os.path.exists(historyPath):
      readline.read_history_file(historyPath)
    atexit.register(save_history)

  __import__("code").interact(banner="", local=local)

