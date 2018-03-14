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
from getpass import getpass
import hmac
import pwd
import grp
import os
import shlex

from slapos.recipe.librecipe import GenericBaseRecipe

def login_shell(password_file, shell):
  if password_file:
    with open(password_file, 'r') as password_file:
      password = password_file.read()

    if not password or hmac.compare_digest(getpass(), password):
      commandline = shlex.split(shell)
      os.execv(commandline[0], commandline)
  return 1

def shellinabox(args):
  certificate_dir = args['certificate_dir']
  certificate_path = os.path.join(certificate_dir, 'certificate.pem')
  with open(certificate_path, 'w') as certificate_file:
    with open(args['ssl_key'], 'r') as key_file:
      # XXX: Dirty hack in order to make shellinabox work
      print >> certificate_file, key_file.read().replace(' PRIVATE ',
                                                         ' RSA PRIVATE ')
    with open(args['ssl_certificate']) as public_key_file:
      print >> certificate_file, public_key_file.read()

  user = pwd.getpwuid(os.getuid()).pw_uid
  group = grp.getgrgid(os.getgid()).gr_gid
  service = '/:%(user)s:%(group)s:%(directory)s:%(command)s' % {
    'user': user,
    'group': group,
    'directory': args['directory'],
    'command': args['login_shell'],
  }

  command_line = [
    args['shellinabox'],
    '-c', certificate_dir,
    '-s', service,
    '--ipv6', args['ipv6'],
    '-p', args['port'],
  ]

  # XXX: By default shellinbox drop privileges
  #      switching to nobody:nogroup user.
  # This force root.
  if group == 'root':
    command_line.extend(['-g', group])
  if user == 'root':
    command_line.extend(['-u', group])

  os.execv(command_line[0], command_line)


class Recipe(GenericBaseRecipe):

  def install(self):
    login_shell_wrapper = self.createPythonScript(
      self.options['login-shell'],
      __name__ + '.login_shell',
      (self.options['password-file'], self.options['shell'])
    )

    shellinabox_wrapper = self.createPythonScript(
      self.options['wrapper'],
      __name__ + '.shellinabox',
      (dict(
        certificate_dir=self.options['certificate-directory'],
        ssl_key=self.options['key-file'],
        ssl_certificate=self.options['cert-file'],
        shellinabox=self.options['shellinabox-binary'],
        directory=self.options['directory'],
        ipv6=self.options['ipv6'],
        port=self.options['port'],
        login_shell=login_shell_wrapper,
       ),)
    )

    return login_shell_wrapper, shellinabox_wrapper
