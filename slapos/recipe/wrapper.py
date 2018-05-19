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

import shlex

from slapos.recipe.librecipe import GenericBaseRecipe

class Recipe(GenericBaseRecipe):
    """Recipe to create a script from given command and options.

    :param str command-line: shell command which launches the intended process
    :param str wrapper-path: absolute path to file's destination

    :param lines wait-for-files: list of files to wait for
    :param lines hash-files: list of files to be checked by hash
    :param str pidfile: path to pidfile ensure exclusivity for the process
    :param str private-dev-shm: size of private /dev/shm, using user namespaces
    :param bool reserve-cpu: command will ask for an exclusive CPU core
    """
    def install(self):
        args = shlex.split(self.options['command-line'])
        wrapper_path = self.options['wrapper-path']
        wait_files = self.options.get('wait-for-files')
        hash_files = self.options.get('hash-files')
        pidfile = self.options.get('pidfile')
        private_dev_shm = self.options.get('private-dev-shm')

        environment = {}
        for line in (self.options.get('environment') or '').splitlines():
          line = line.strip()
          if line:
            k, v = line.split('=')
            environment[k.rstrip()] = v.lstrip()

        kw = {}
        if wait_files:
          kw['wait_list'] = wait_files.split()
        if pidfile:
          kw['pidfile'] = pidfile
        if private_dev_shm:
          kw['private_dev_shm'] = private_dev_shm
        if self.isTrueValue(self.options.get('reserve-cpu')):
          kw['reserve_cpu'] = True
        if hash_files:
          hash_file_list = hash_files.split()
          hash = self.generateHashFromFiles(hash_file_list)
          wrapper_path = "%s-%s" % (wrapper_path, hash)

        return self.createWrapper(wrapper_path, args, environment, **kw)

    def generateHashFromFiles(self, file_list):
      import hashlib
      hasher = hashlib.md5()
      for path in file_list:
        with open(path, 'r') as afile:
          buf = afile.read()
        hasher.update("%s\n" % len(buf))
        hasher.update(buf)
      hash = hasher.hexdigest()
      return hash
