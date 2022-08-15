##############################################################################
#
# Copyright (c) 2011 Vifib SARL and Contributors. All Rights Reserved.
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
from slapos.recipe.librecipe import GenericBaseRecipe
import sys
import os

class Recipe(GenericBaseRecipe):
  """
  Create script that will check if "url" is available (e.g page answers 200 OK).
  """

  def install(self):
    timeout_file = os.path.join(os.getcwd(), 'etc/promise_timeout')
    config = {
      'url': self.options['url'],
      'shell_path': self.options['dash_path'],
      'curl_path': self.options['curl_path'],
      'check_secure': self.options.get('check-secure', 0),
      'http_code': self.options.get('http_code', '200'),
      'time_out': self.options.get('timeout-file-path', timeout_file),
      'ca-cert-file': self.options.get('ca-cert-file', ''),
      'cert-file': self.options.get('cert-file', ''),
      'key-file': self.options.get('key-file', ''),
    }

    # XXX-Cedric in this script, curl won't check certificate
    promise = self.createExecutable(
      self.options['path'],
      self.substituteTemplate(self.getTemplateFilename('check_url.in'), config)
    )

    return [promise]
