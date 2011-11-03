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
import subprocess
import sys

from slapos.recipe.librecipe import GenericBaseRecipe
from slapos import slap as slapmodule


def promise(args):
  slap = slapmodule.slap()
  slap.initializeConnection(args['server_url'],
    key_file=args.get('key_file'), cert_file=args.get('cert_file'))
  partition = slap.registerComputerPartition(args['computer_id'],
                                             args['partition_id'])

  # Rdiff Backup protocol quit command
  quitcommand = 'q' + chr(255) + chr(0) * 7
  ssh_cmdline = [args['ssh_client'], '-T',
                 '-i', args['key'],
                 '-y', '%(user)s@%(host)s/%(port)s' % args]

  ssh = subprocess.Popen(ssh_cmdline, stdin=subprocess.PIPE,
                         stdout=open(os.devnull), stderr=open(os.devnull))
  ssh.stdin.write(quitcommand)
  ssh.stdin.flush()
  ssh.stdin.close()

  if ssh.wait() != 0:
    # Bad python 2 syntax, looking forward python 3 to have print(file=)
    print >> sys.stderr, "SSH Connection failed"
    partition.bang("SSH Connection failed. rdiff-backup is unusable.")

  return ssh.returncode

class Recipe(GenericBaseRecipe):

  def install(self):
    command = [self.options['rdiffbackup-binary']]

    if self.optionIsTrue('client', True):
      self.logger.info("Client mode")

      # XXX-Antoine: Automaticaly accept unknown key with -y
      # we should generate a known_host file.
      remote_schema = '%(ssh)s -i %%s -T -y %(user)s@%(host)s/%(port)s' % \
        {
          'ssh': self.options['sshclient-binary'],
          'user': self.options['user'],
          'host': self.options['host'],
          'port': self.options['port'],
        }

      command.extend(['--remote-schema', remote_schema])
      command.append('%(key)s::%(path)s' % {'key': self.options['key'],
                                            'path': self.options['path']})
      command.append(self.options['localpath'])

      if 'promise' in self.options:
        slap_connection = self.buildout['slap-connection']
        self.createPythonScript(self.options['promise'],
          __name__ + '.promise',
          dict(
            server_url=slap_connection['server-url'],
            computer_id=slap_connection['computer-id'],
            cert_file=slap_connection.get('cert-file'),
            key_file=slap_connection.get('key-file'),
            partition_id=slap_connection['partition-id'],
            ssh_client=self.options['sshclient-binary'],
            user=self.options['user'],
            host=self.options['host'],
            port=self.options['port'],
            key=self.options['key'],
          ),
        )

    else:
      self.logger.info("Server mode")
      command.extend(['--restrict', self.options['path']])
      command.append('--server')

    wrapper = self.createPythonScript(
      self.options['wrapper'],
      'slapos.recipe.librecipe.execute.execute',
      command)

    return [wrapper]
