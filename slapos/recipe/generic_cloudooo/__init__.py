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
import zc.buildout
from slapos.recipe.librecipe import GenericBaseRecipe

def compareMimetypeEntryPair(a, b):
  """
    Like comparing strings, but here the star `*` is stronger than any other
    character.
  """
  i = 0
  for i in range(min(len(a), len(b))):
    if a[i] != b[i]:
      if a[i] == "*": return 1
      if b[i] == "*": return -1
      if a[i] < b[i]: return -1
      if a[i] > b[i]: return 1
      return 0
  if a[i:i+1]: return 1
  if b[i:i+1]: return -1
  return 0

default_mimetype_entry_list = [
  "application/vnd.oasis.opendocument* * ooo",
  "application/vnd.sun.xml* * ooo",
  "application/pdf text/* pdf",
  "application/pdf * ooo",
  "video/* * ffmpeg",
  "audio/* * ffmpeg",
  "application/x-shockwave-flash * ffmpeg",
  "application/ogg * ffmpeg",
  "application/ogv * ffmpeg",
  "image/png image/jpeg imagemagick",
  "image/png * ooo",
  "image/* image/* imagemagick",
  "text/* * ooo",
  "application/zip * ooo",
  "application/msword * ooo",
  "application/vnd* * ooo",
  "application/x-vnd* * ooo",
  "application/postscript * ooo",
  "application/wmf * ooo",
  "application/csv * ooo",
  "application/x-openoffice-gdimetafile * ooo",
  "application/x-emf * ooo",
  "application/emf * ooo",
  "application/octet* * ooo",
  "* application/vnd.oasis.opendocument* ooo",
]

class Recipe(GenericBaseRecipe):
  def install(self):
    path_list = []
    conversion_server_dict = dict(
      working_path=self.options['data-directory'],
      uno_path=self.options['ooo-uno-path'],
      office_binary_path=self.options['ooo-binary-path'],
      ip=self.options['ip'],
      port=int(self.options['port']),
      openoffice_port=int(self.options['openoffice-port']),
    )
    environment_variable_list = []
    for env_line in self.options['environment'].splitlines():
      env_line = env_line.strip()
      if not env_line:
        continue
      if '=' in env_line:
        env_key, env_value = env_line.split('=')
        environment_variable_list.append((env_key.strip(), env_value.strip()))
      else:
        raise zc.buildout.UserError('Line %r in environment parameter is '
            'incorrect' % env_line)
    conversion_server_dict['ENVIRONMENT_VARIABLE_LIST'] = '\n'.join(
      ['env-%s = %s' % (key, value) for key, value in environment_variable_list]
      )
    mimetype_entry_list = [
      l.strip()
      for l in self.options.get('mimetype_entry_addition', '').splitlines()
      if l and not l.isspace()
    ]
    mimetype_entry_list.extend(default_mimetype_entry_list)
    mimetype_entry_list.sort(compareMimetypeEntryPair)
    conversion_server_dict['MIMETYPE_ENTRY_LIST'] = \
      "\n".join(["  " + l for l in mimetype_entry_list])
    config_file = self.createFile(self.options['configuration-file'],
        self.substituteTemplate(self.getTemplateFilename('cloudooo.cfg.in'),
          conversion_server_dict))
    path_list.append(config_file)
    path_list.append(self.createPythonScript(self.options['wrapper'],
     'slapos.recipe.librecipe.execute.execute_with_signal_translation',
      [self.options['ooo-paster'].strip(), 'serve', config_file]))
    return path_list
