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
import os
import signal
import subprocess
import sys
import urlparse

from slapos.recipe.librecipe import GenericSlapRecipe
from slapos.recipe.dropbear import KnownHostsFile
from slapos.recipe.notifier import Notify
from slapos.recipe.notifier import Callback
from slapos import slap as slapmodule


def promise(args):

  def failed_ssh():
    sys.stderr.write("SSH Connection failed\n")
    partition = slap.registerComputerPartition(args['computer_id'],
                                               args['partition_id'])
    partition.bang("SSH Connection failed. rdiff-backup is unusable.")

  def sigterm_handler(signum, frame):
    failed_ssh()

  signal.signal(signal.SIGTERM, sigterm_handler)

  slap = slapmodule.slap()
  slap.initializeConnection(args['server_url'],
                            key_file=args.get('key_file'),
                            cert_file=args.get('cert_file'))

  ssh = subprocess.Popen([args['ssh_client'], '%(user)s@%(host)s/%(port)s' % args],
                         stdin=subprocess.PIPE,
                         stdout=open(os.devnull, 'w'),
                         stderr=open(os.devnull, 'w'))

  # Rdiff Backup protocol quit command
  quitcommand = 'q' + chr(255) + chr(0) * 7

  ssh.stdin.write(quitcommand)
  ssh.stdin.flush()
  ssh.stdin.close()
  ssh.wait()

  if ssh.poll() is None:
    return 1
  if ssh.returncode != 0:
    failed_ssh()
  return ssh.returncode



class Recipe(GenericSlapRecipe, Notify, Callback):

  def add_slave(self, entry, known_hosts_file):
    path_list = []

    url = entry.get('url')
    if not url:
      raise ValueError('Missing URL parameter for PBS recipe')
    parsed_url = urlparse.urlparse(url)

    slave_id = entry['notification-id']
    slave_type = entry['type']
    if not slave_type in ['pull', 'push']:
      raise ValueError('type parameter must be either pull or push.')

    promise_path = os.path.join(self.options['promises-directory'], slave_id)
    promise_dict = self.promise_base_dict.copy()
    promise_dict.update(user=parsed_url.username,
                        host=parsed_url.hostname,
                        port=parsed_url.port)
    promise = self.createPythonScript(promise_path,
                                      __name__ + '.promise',
                                      promise_dict)
    path_list.append(promise)

    host = parsed_url.hostname
    known_hosts_file[host] = entry['server-key']

    notifier_path = os.path.join(self.options['wrappers-directory'], slave_id)
    rdiff_path = notifier_path + '_raw'

    # Create the rdiff-backup wrapper
    # It is useful to separate it from the notifier so that we can run it
    # Manually.
    rdiff_parameter_list = []
    # XXX use -y because the host might not yet be in the
    #     trusted hosts file until the next time slapgrid is run.
    rdiff_parameter_list.extend([
        '--remote-schema', '%(ssh)s -y -p %%s %(user)s@%(host)s' % {
            'ssh': self.options['sshclient-binary'],
            'user': parsed_url.username,
            'host': parsed_url.hostname,
    }])
    if slave_type == 'push':
      rdiff_parameter_list.extend(['--restore-as-of', 'now', '--force'])
      comments = ['','Push data to a PBS *-import instance.', '']
    elif slave_type == 'pull':
      comments = ['','Pull data from a PBS *-export instance.', '']
    remote_directory = '%(port)s::%(path)s' % {'port': parsed_url.port,
                                               'path': parsed_url.path}
    local_directory = self.createDirectory(self.options['directory'], entry['name'])
    rdiff_parameter_list.extend([local_directory, remote_directory])
    rdiff_wrapper = self.createWrapper(
        name=rdiff_path,
        command=self.options['rdiffbackup-binary'],
        parameters=rdiff_parameter_list,
        comments=comments,
    )
    path_list.append(rdiff_wrapper)

    # Create notifier wrapper
    notifier_wrapper = self.createNotifier(
        notifier_binary=self.options['notifier-binary'],
        wrapper=notifier_path,
        executable=rdiff_wrapper,
        log=os.path.join(self.options['feeds'], entry['notification-id']),
        title=entry.get('title', slave_id),
        notification_url=entry['notify'],
        feed_url='%s/get/%s' % (self.options['notifier-url'], entry['notification-id']),
    )
    path_list.append(notifier_wrapper)

    if 'on-notification' in entry:
      path_list.append(self.createCallback(str(entry['on-notification']),
                                           notifier_wrapper))
    else:
      cron_entry = os.path.join(self.options['cron-entries'], slave_id)
      with open(cron_entry, 'w') as cron_entry_file:
        cron_entry_file.write('%s %s' % (entry['frequency'], notifier_wrapper))
      path_list.append(cron_entry)

    return path_list


  def _install(self):
    path_list = []

    if self.optionIsTrue('client', True):
      self.logger.info("Client mode")

      slap_connection = self.buildout['slap-connection']
      self.promise_base_dict = {
              'server_url': slap_connection['server-url'],
              'computer_id': slap_connection['computer-id'],
              'cert_file': slap_connection.get('cert-file'),
              'key_file': slap_connection.get('key-file'),
              'partition_id': slap_connection['partition-id'],
              'ssh_client': self.options['sshclient-binary'],
        }

      slaves = json.loads(self.options['slave-instance-list'])
      known_hosts = KnownHostsFile(self.options['known-hosts'])
      with known_hosts:
        for slave in slaves:
          path_list.extend(self.add_slave(slave, known_hosts))
    else:
      self.logger.info("Server mode")

      wrapper = self.createWrapper(name=self.options['wrapper'],
                                   command=self.options['rdiffbackup-binary'],
                                   parameters=[
                                       '--restrict', self.options['path'],
                                       '--server'
                                       ])
      path_list.append(wrapper)

    return path_list

