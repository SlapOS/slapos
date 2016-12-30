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
import errno, os
from slapos.recipe.librecipe import GenericBaseRecipe

class KnownHostsFile(dict):

  def __init__(self, filename):
    self._filename = filename

  def _load(self):
    if os.path.exists(self._filename):
      with open(self._filename, 'r') as keyfile:
        for line in keyfile:
          if line.strip() == "":
            continue
          host, key = [column.strip() for column in line.split(' ', 1)]
          self[host] = key

  def _dump(self):
    with open(self._filename, 'w') as keyfile:
      for key, value in self.items():
        if key is not None and value is not None:
          keyfile.write('%(host)s %(key)s\n' % {'host': key,
                                                'key': value})

  def __enter__(self):
    self._load()

  def __exit__(self, exc_type, exc_value, traceback):
    self._dump()

class Recipe(GenericBaseRecipe):

  def install(self):
    path_list = []

    dropbear_cmd = [self.options['dropbear-binary']]
    # Don't fork into background
    dropbear_cmd.append('-F')
    # Log on stderr
    dropbear_cmd.append('-E')
    # Don't display motd
    dropbear_cmd.append('-m')
    # Disable password login
    dropbear_cmd.extend(['-s', '-g'])
    # Disable port forwarding
    if not self.optionIsTrue('allow-port-forwarding', default=False):
      dropbear_cmd.extend(['-j', '-k'])

    host = self.options['host']
    if ':' in host:
      host = '[%s]' % host
    port = self.options['port']
    binding_address = '%s:%s' % (host, port)
    dropbear_cmd.extend(['-p', binding_address])
    # Single user mode
    dropbear_cmd.append('-n')
    # Keep connection alive for 5 minutes
    dropbear_cmd.extend(['-K', '300'])

    if 'dss-keyfile' in self.options:
      dropbear_cmd.extend(['-d', self.options['dss-keyfile']])
    else:
      dropbear_cmd.extend(['-r', self.options['rsa-keyfile']])

    env = {}
    if 'home' in self.options:
      env['DROPBEAR_OVERRIDE_HOME'] = self.options['home']

    if 'shell' in self.options:
      env['DROPBEAR_OVERRIDE_SHELL'] = self.options['shell']

    wrapper = self.createPythonScript(
      self.options['wrapper'],
      'slapos.recipe.librecipe.execute.executee',
      (dropbear_cmd, env, )
    )
    path_list.append(wrapper)

    return path_list

class Client(GenericBaseRecipe):

  def install(self):
    env = dict()

    if 'home' in self.options:
      env['HOME'] = self.options['home']
      self.createDirectory(self.options['home'], '.ssh')

    dropbear_cmd = [self.options['dbclient-binary'], '-T']
    if self.optionIsTrue('force-host-key', default=False):
      dropbear_cmd.extend(['-y'])

    if 'identity-file' in self.options:
      dropbear_cmd.extend(['-i', self.options['identity-file']])

    wrapper = self.createPythonScript(
      self.options['wrapper'],
      'slapos.recipe.librecipe.execute.executee',
      (dropbear_cmd, env, )
    )

    return [wrapper]


class AddAuthorizedKey(GenericBaseRecipe):

  def install(self):
    key = self.options['key']
    ssh = self.createDirectory(self.options['home'], '.ssh')
    filename = os.path.join(ssh, 'authorized_keys')
    try:
        with open(filename) as f:
            if f.read() == key:
                return [filename]
    except IOError as e:
        if e.errno != errno.ENOENT:
            raise
    # Atomic update.
    tmp = filename + '.new'
    try:
        with open(tmp, 'w') as f:
            f.write(key)
        os.rename(tmp, filename)
    finally:
        try:
            os.remove(tmp)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
    return [filename]
