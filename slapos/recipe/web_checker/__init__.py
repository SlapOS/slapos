##############################################################################
#
# Copyright (c) 2012 Vifib SARL and Contributors. All Rights Reserved.
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
import os
import re
from slapos.recipe.librecipe import GenericSlapRecipe

class Recipe(GenericSlapRecipe):
  """
    Create web checker configuration.
  """
  def _install(self):
    path_list = []
    try:
      web_checker_mail_address = self.options['mail-address']
      web_checker_smtp_host = self.options['smtp-host']
      web_checker_frontend_url = self.options['frontend-url']
    except KeyError:
      # BBB
      web_checker_mail_address = self.parameter_dict['web-checker-mail-address']
      web_checker_smtp_host = self.parameter_dict['web-checker-smtp-host']
      web_checker_frontend_url = self.parameter_dict['web-checker-frontend-url']
    web_checker_working_directory = \
      self.options['web-checker-working-directory']
    config = dict(
      web_checker_mail_address = web_checker_mail_address,
      web_checker_smtp_host = web_checker_smtp_host,
      web_checker_working_directory = web_checker_working_directory,
      frontend_url = web_checker_frontend_url,
      wget_binary_path = self.options['wget-binary-path'],
      varnishlog_binary_path = self.options['varnishlog-binary-path'],
      web_checker_log = self.options['web-checker-log'],
    )
    path_list.append(self.createFile(self.options['web-checker-config'],
      self.substituteTemplate(self.getTemplateFilename('web_checker.cfg.in'),
        config)))
    return path_list
