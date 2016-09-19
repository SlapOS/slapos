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
import json
import hashlib
import os
import subprocess
import re

from slapos.recipe.librecipe import GenericBaseRecipe
from slapos.recipe.librecipe.inotify import subfiles

# This authority only works with dropbear or openssh sshkey generators
def sshkeys_authority(args):
  requests_directory = args['requests']
  keygen_binary = args['sshkeygen']

  if 'openssh' in keygen_binary:
    authority_type = 'openssh'
  else:
    # Keep dropbear for compatibility
    authority_type = 'dropbear'

  for request_filename in subfiles(requests_directory):

    with open(request_filename) as request_file:
      request = json.load(request_file)

    key_type = request.get('type', 'rsa')
    size = str(request.get('size', 4096))
    try:
      private_key = request['private_key']
      public_key = request['public_key']
    except KeyError:
      break

    if not os.path.exists(private_key):
      if os.path.exists(public_key):
        os.unlink(public_key)
      if authority_type == 'openssh':
        keygen_cmd = [keygen_binary, '-N', "", '-C', "", '-t', key_type,
                      '-f', private_key, '-b', size]
      else:
        keygen_cmd = [keygen_binary, '-t', key_type, '-f', private_key,
                      '-s', size]
      # If the keygeneration return an non-zero status, it means there's a
      # big problem. Let's exit in this case
      subprocess.check_call(keygen_cmd, env=os.environ.copy())

    if not os.path.exists(public_key):
      keygen_cmd = [keygen_binary, '-f', private_key, '-y']

      keygen = subprocess.Popen(keygen_cmd, stdout=subprocess.PIPE,
                                stdin=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                env=os.environ.copy())
      keygen.stdin.flush()
      keygen.stdin.close()

      # If the keygeneration return an non-zero status, it means there's a
      # big problem. Let's exit in this case
      if keygen.wait() != 0:
        raise subprocess.CalledProcessError("%r returned a non-zero status" % \
                                            ' '.join(keygen_cmd))
      public_key_value = ''
      for line in keygen.stdout:
        # Perl programming !
        # Don't worry, just regex to detect the ssh public key line
        matchresult = re.match(r'ssh-.*?=+', line)
        if matchresult:
          public_key_value = matchresult.group(0)
          break

      with open(public_key, 'w') as public_key_file:
        public_key_file.write(public_key_value)



class Recipe(GenericBaseRecipe):

  def install(self):
    args = dict(
      requests=self.options['request-directory'],
      sshkeygen=self.options['keygen-binary'],
    )

    wrapper = self.createPythonScript(self.options['wrapper'],
      __name__ + '.sshkeys_authority', args)
    return [wrapper]

class Request(GenericBaseRecipe):

  def _options(self, options):
    if 'name' not in options:
      options['name'] = self.name

    keys_directory = options['keys-directory']

    self.private_key = os.path.join(keys_directory,
      hashlib.sha256(options['name']).hexdigest())
    self.public_key = self.private_key + '.pub'

    options['public-key-value'] = ''
    if os.path.exists(self.public_key):
      key_content = open(self.public_key).read()
      if key_content:
        options['public-key-value'] = key_content

  def install(self):
    requests_directory = self.options['request-directory']
    request_file = os.path.join(requests_directory, self.options['name'])

    request = dict(
      private_key=self.private_key,
      public_key=self.public_key,
    )
    if 'size' in self.options:
      request.update(size=int(self.options['size'], 10))
    if 'type' in self.options:
      request.update(type=self.options['type'])

    with open(request_file, 'w') as file_:
      json.dump(request, file_)

    public_key_link, private_key_link = (self.options['public-key'],
                                         self.options['private-key'],
                                        )
    # XXX: Copy and past from certificate_authority/__init__.py:Request
    # We should factorize that
    for link in [public_key_link, private_key_link]:
      if os.path.islink(link):
        os.unlink(link)
      elif os.path.exists(link):
        raise OSError("%r should be a symbolic link." % link)

    os.symlink(self.public_key, public_key_link)
    os.symlink(self.private_key, private_key_link)
    # end-XXX

    wrapper = self.createPythonScript(
      self.options['wrapper'],
      'slapos.recipe.librecipe.execute.execute_wait',
      [ [self.options['executable']],
        [self.private_key, self.public_key] ])


    return [request_file, wrapper, public_key_link, private_key_link]
