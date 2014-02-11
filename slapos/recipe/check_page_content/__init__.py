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

class Recipe(GenericBaseRecipe):
  """
  Create script that will check if content at "url" is available
  (e.g page has a link to itself).
  """

  def install(self):
    url = self.options['url'].strip()
    config = {
      'url': url,
      'shell_path': self.options['dash_path'],
      'curl_path': self.options['curl_path'],
      'match': self.options.get('match', url)
    }

    # XXX-Cedric in this script, curl won't check certificate
    promise = self.createExecutable(
      self.options['path'],
      self.substituteTemplate(self.getTemplateFilename('check_page_content.in'), config)
    )

    return [promise]
