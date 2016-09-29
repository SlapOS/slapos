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
import os
import itertools
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



class AuthorizedKeysFile(object):

  def __init__(self, filename):
    self.filename = filename

  def append(self, key):
    """Append the key to the file if the key's not in the file
    """
    # Create the file it it does not exist
    try:
      file_ = os.open(self.filename, os.O_CREAT | os.O_EXCL)
      os.close(file_)
    except:
      pass

    with open(self.filename, 'r') as keyfile:
      # itertools.imap avoid loading all the authorized_keys file in
      # memory which would be counterproductive.
      present = (key.strip() in itertools.imap(lambda k: k.strip(),
                                               keyfile))
      try:
        keyfile.seek(-1, os.SEEK_END)
        ended_by_newline = (keyfile.read() == '\n')
      except IOError:
        ended_by_newline = True

    if not present:
      with open(self.filename, 'a') as keyfile:
        if not ended_by_newline:
          keyfile.write('\n')
        keyfile.write(key.strip())

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


def keysplit(s):
  """
  Split a string like "ssh-rsa AKLFKJSL..... ssh-rsa AAAASAF...."
  and return the individual key_type + key strings.

  TODO: handle comments in ssh keys, which are generated
        by default at key creation.
  """
  s = s.replace('\n', ' ')
  si = iter(s.split(' '))
  while True:
    key_type = next(si)
    if key_type == '':
      continue
    try:
      key_value = next(si)
    except StopIteration:
      # odd number of elements, should not happen
      break
    yield '%s %s' % (key_type, key_value)


class AddAuthorizedKey(GenericBaseRecipe):

  def install(self):
    ssh = self.createDirectory(self.options['home'], '.ssh')

    authorized_keys = AuthorizedKeysFile(os.path.join(ssh, 'authorized_keys'))
    for key in keysplit(self.options['key']):
      # XXX key might actually be the string 'None' or 'null'
      authorized_keys.append(key)

    return [authorized_keys.filename]

