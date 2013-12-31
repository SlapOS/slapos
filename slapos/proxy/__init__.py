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

  def mergeConfig(self, args, configp):
    # Set options parameters
    for option, value in args.__dict__.items():
      setattr(self, option, value)

    # Merge the arguments and configuration
    for section in ("slapproxy", "slapos"):
      configuration_dict = dict(configp.items(section))
      for key in configuration_dict:
        if not getattr(self, key, None):
          setattr(self, key, configuration_dict[key])


  def setConfig(self):
    if not self.database_uri:
      raise ValueError('database-uri is required.')


def do_proxy(conf):
  from slapos.proxy.views import app
  for handler in conf.logger.handlers:
    app.logger.addHandler(handler)
  app.logger.setLevel(logging.INFO)
  app.config['computer_id'] = conf.computer_id
  app.config['DATABASE_URI'] = conf.database_uri
  app.config['software_product_list'] = \
    _generateSoftwareProductListFromString(
      getattr(conf, 'software_product_list', ""))
  app.run(host=conf.host, port=int(conf.port))
