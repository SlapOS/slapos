# -*- coding: utf-8 -*-
# vim: set et sts=2:
##############################################################################
#
# Copyright (c) 2010, 2011, 2012, 2013 Vifib SARL and Contributors.
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

import logging

from slapos.proxy.views import app
from slapos.util import sqlite_connect

def _generateSoftwareProductListFromString(software_product_list_string):
  """
  Take a string as argument (which usually comes from the software_product_list
  parameter of the slapproxy configuration file), and parse it to generate
  list of Software Products that slapproxy will use.
  """
  try:
    software_product_string_split = software_product_list_string.split('\n')
  except AttributeError:
    return {}
  software_product_list = {}
  for line in software_product_string_split:
    if line:
      software_reference, url = line.split(' ')
      software_product_list[software_reference] = url
  return software_product_list


class ProxyConfig(object):
  def __init__(self, logger):
    self.logger = logger
    self.multimaster = {}
    self.software_product_list = []

  def mergeConfig(self, args, configp):
    # Set arguments parameters (from CLI) as members of self
    for option, value in args.__dict__.items():
      setattr(self, option, value)

    for section in configp.sections():
      configuration_dict = dict(configp.items(section))
      if section in ("slapproxy", "slapos"):
        # Merge the arguments and configuration as member of self
        for key in configuration_dict:
          if not getattr(self, key, None):
            setattr(self, key, configuration_dict[key])
      elif section.startswith('multimaster/'):
        # Merge multimaster configuration if any
        # XXX: check for duplicate SR entries
        for key, value in configuration_dict.iteritems():
          if key == 'software_release_list':
            # Split multi-lines values
            configuration_dict[key] = [line.strip() for line in value.strip().split('\n')]
        self.multimaster[section.split('multimaster/')[1]] = configuration_dict

  def setConfig(self):
    if not self.database_uri:
      raise ValueError('database-uri is required.')
    # XXX: check for duplicate SR entries.
    self.software_product_list = _generateSoftwareProductListFromString(
        getattr(self, 'software_product_list', ''))


def setupFlaskConfiguration(conf):
  app.config['computer_id'] = conf.computer_id
  app.config['DATABASE_URI'] = conf.database_uri
  app.config['software_product_list'] = conf.software_product_list
  app.config['multimaster'] = conf.multimaster

def connectDB():
  # if first connection, create an empty db at DATABASE_URI path
  conn = sqlite_connect(app.config['DATABASE_URI'])
  conn.close()

def do_proxy(conf):
  for handler in conf.logger.handlers:
    app.logger.addHandler(handler)
  app.logger.setLevel(logging.INFO)
  setupFlaskConfiguration(conf)
  connectDB()
  app.run(host=conf.host, port=int(conf.port), threaded=True)

