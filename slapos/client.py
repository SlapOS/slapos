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

import atexit
import ConfigParser
import os
import sys

import slapos.slap.slap
from slapos.slap import SoftwareProductCollection

SOFTWARE_PRODUCT_NAMESPACE = "product."

class ClientConfig(object):
  state = None

  def __init__(self, args, configp=None):
    # XXX configp cannot possibly be optional
    """
    Set options given by parameters.
    """
    # Set options parameters
    for key, value in args.__dict__.items():
      setattr(self, key, value)

    # Merges the arguments and configuration
    try:
      configuration_dict = dict(configp.items('slapconsole'))
    except ConfigParser.NoSectionError:
      pass
    else:
      for key in configuration_dict:
        if not getattr(self, key, None):
          setattr(self, key, configuration_dict[key])
    configuration_dict = dict(configp.items('slapos'))
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
      self.master_url = master_url

    self.master_rest_url = configuration_dict.get('master_rest_url')

    if self.key_file:
        self.key_file = os.path.expanduser(self.key_file)

    if self.cert_file:
        self.cert_file = os.path.expanduser(self.cert_file)


def init(conf, logger):
  """Initialize Slap instance, connect to server and create
  aliases to common software releases"""
  # XXX check certificate and key existence
  slap = slapos.slap.slap()
  slap.initializeConnection(conf.master_url,
      key_file=conf.key_file, cert_file=conf.cert_file,
      slapgrid_rest_uri=conf.master_rest_url)
  local = globals().copy()
  local['slap'] = slap
  # Create global shortcut functions to request instance and software
  def shorthandRequest(*args, **kwargs):
    return slap.registerOpenOrder().request(*args, **kwargs)
  def shorthandSupply(*args, **kwargs):
    # XXX-Cedric Implement computer_group support
    return slap.registerSupply().supply(*args, **kwargs)
  local['request'] = shorthandRequest
  local['supply'] = shorthandSupply
  local['product'] = SoftwareProductCollection(logger, slap)

  return local

def _getSoftwareReleaseFromSoftwareString(logger, software_string, product):
    """
    If Software string is a product:
    Return the best Software Release URL of the Software Product "X" of the
    string "product.X".
    Else, return as is.
    """
    if not software_string.startswith(SOFTWARE_PRODUCT_NAMESPACE):
        return software_string

    try:
        return product.__getattr__(software_string[len(SOFTWARE_PRODUCT_NAMESPACE):])
    except AttributeError as e:
       logger.error('Error: %s Exiting now.' % e.message)
       sys.exit(1)

def do_console(local):
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
