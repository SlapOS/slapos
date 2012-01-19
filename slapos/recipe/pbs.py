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
from json import loads as unjson
from hashlib import sha512
import urlparse
import os
import subprocess
import sys
import signal
import inspect
import uuid
import base64
import urllib

from slapos.recipe.librecipe import GenericSlapRecipe
from slapos.recipe.dropbear import KnownHostsFile
from slapos import slap as slapmodule


def process_backup(config):
  from glob import glob

  runafter = config['run_after']
  pull_script = config['pull']
  push_scripts = glob(config['push'])
  os.execv(runafter, [runafter] + ['--first-one', pull_script] + push_scripts)


def promise(args):

  def failed_ssh(partition, ssh):
    # Bad python 2 syntax, looking forward python 3 to have print(file=)
    print >> sys.stderr, "SSH Connection failed"
    try:
      ssh.terminate()
    except:
      pass
    partition.bang("SSH Connection failed. rdiff-backup is unusable.")

  def sigterm_handler(signum, frame):
    # Walk up in the stack to get promise local
    # variables
    ssh = None
    for upper_frame in inspect.getouterframes(frame):
      # Use promise.func_name insteand of 'promise' in order to be
      # detected by editor if promise func name change.
      # Else, it's hard to debug this kind of error.
      if upper_frame[3] == promise.func_name:
        try:
          partition = upper_frame[0].f_locals['partition']
          ssh = upper_frame[0].f_locals['ssh']
        except KeyError:
          raise SystemExit("SIGTERM Send too soon.")
        break
    # If ever promise function wasn't found in the stack.
    if ssh is None:
      raise SystemExit
    failed_ssh(partition, ssh)

  signal.signal(signal.SIGTERM, sigterm_handler)

  slap = slapmodule.slap()
  slap.initializeConnection(args['server_url'],
    key_file=args.get('key_file'), cert_file=args.get('cert_file'))
  partition = slap.registerComputerPartition(args['computer_id'],
                                             args['partition_id'])

  # Rdiff Backup protocol quit command
  quitcommand = 'q' + chr(255) + chr(0) * 7
  ssh_cmdline = [args['ssh_client'], '%(user)s@%(host)s/%(port)s' % args]

  ssh = subprocess.Popen(ssh_cmdline, stdin=subprocess.PIPE,
                         stdout=open(os.devnull), stderr=open(os.devnull))
  ssh.stdin.write(quitcommand)
  ssh.stdin.flush()
  ssh.stdin.close()
  ssh.wait()

  if ssh.poll() is None:
    return 1
  if ssh.returncode != 0:
    failed_ssh(partition, ssh)
  return ssh.returncode


class Recipe(GenericSlapRecipe):

  def _options(self, options):
    if self.optionIsTrue('client', True):
      slaves = unjson(options['slave-instance-list'])
      options['peers'] = '\n'.join([str(entry['request-agent-url'])
                                    for entry in slaves])

  def add_slave_promise(self, parsed_url, instance_id):
    promise_path = os.path.join(self.options['promises-directory'],
                                instance_id)
    promise_dict = self.promise_base_dict.copy()
    promise_dict.update(user=parsed_url.username,
                        host=parsed_url.hostname,
                        port=parsed_url.port)
    promise = self.createPythonScript(promise_path,
                                      __name__ + '.promise',
                                      promise_dict)
    self.path_list.append(promise)

  def add_slave(self, entry, known_hosts_file):
    url = entry.get('url')
    if url is None:
      url = ''

    # Base32 is filename safe
    backup_id = base64.b32encode(uuid.UUID(entry['id']).bytes)
    instance_id = '%(uuid)s%(type)s%(id)s' % {
      'uuid': backup_id,
      'type': entry['type'],
      'id': entry['slave_reference']
    }
    parsed_url = urlparse.urlparse(url)

    self.add_slave_promise(parsed_url, instance_id)

    host = parsed_url.hostname
    known_hosts_file[host] = entry['authorized-key']

    remote_schema = '%(ssh)s -p %%s %(user)s@%(host)s' % {
        'ssh': self.options['sshclient-binary'],
        'user': parsed_url.username,
        'host': parsed_url.hostname,
    }

    agent_url = self.options['agent-url']
    feed_url = urlparse.urljoin(self.options['agent-url'],
                                'log/%s' % urllib.quote(instance_id))
    notify_url = urlparse.urljoin(self.options['agent-url'],
                                  'notify')

    command = [self.options['notifier-binary'],
               '--write', feed_url,
               '--title', entry.get('name', 'Untitled'),
              ]

    for notify in entry.get('notify', '').split():
      if notify: # Ignore empty values
        command.extend(['--notify', notify])
    command.append('--')

    command.extend([self.options['rdiffbackup-binary'], '--remote-schema', remote_schema])

    remote_directory = '%(port)s::%(path)s' % {'port': parsed_url.port,
                                               'path': parsed_url.path}

    local_directory = self.createDirectory(self.options['directory'],
                                           backup_id)

    if entry['type'] == 'push':
      command.extend(['--restore-as-of', 'now'])
      command.append('--force')
      command.extend([local_directory, remote_directory])
    else:
      command.extend([remote_directory, local_directory])

    wrapper_path = os.path.join(self.options['wrappers-directory'],
                                instance_id)

    self.path_list.append(self.createPythonScript(
      wrapper_path,
      'slapos.recipe.librecipe.execute.execute',
      command,
    ))

    if entry['type'] == 'pull':
      backup_wrapper = os.path.join(self.options['wrapper-directory'],
                                    backup_id)
      push_pattern = os.path.join(self.options['wrapper-directory'],
                                  '%spush*' % backup_id)
      self.path_list.append(self.createPythonScript(
        backup_wrapper,
        __name__ + '.process_backup',
        {
          'run_after': self.options['runafter-binary'],
          'pull': wrapper_path,
          'push': push_pattern,
        }
      ))

      if 'frequency' in entry:
        cron_entry_filename = os.path.join(self.options['cron-entries'],
                                           '%s-%s' % (self.name, backup_id))
        self.path_list.append(self.createFile(cron_entry_filename,
          '%s %s' % (entry['frequency'], backup_wrapper)))
      elif 'trigger-feed' in entry:
        trigger_filename = os.path.join(self.options['agent-callbacks-directory'],
                                        sha512(entry['trigger-feed']).hexdigest())
        with open(trigger_filename, 'w') as trigger_file:
          trigger_file.write(backup_wrapper)
        self.path_list.append(trigger_filename)

    self.setConnectionDict({
      'agent-url': agent_url,
      'feed-url': feed_url,
      'notify-url': notify_url,
    }, entry['slave_reference'])

  def _install(self):
    self.path_list = []


    if self.optionIsTrue('client', True):
      self.logger.info("Client mode")

      slap_connection = self.buildout['slap-connection']
      self.promise_base_dict = dict(
        server_url=slap_connection['server-url'],
        computer_id=slap_connection['computer-id'],
        cert_file=slap_connection.get('cert-file'),
        key_file=slap_connection.get('key-file'),
        partition_id=slap_connection['partition-id'],
        ssh_client=self.options['sshclient-binary'],
      )

      slaves = unjson(self.options['slave-instance-list'])
      known_hosts = KnownHostsFile(self.options['known-hosts'])
      with known_hosts:
        for slave in slaves:
          self.add_slave(slave, known_hosts)

    else:
      command = [self.options['rdiffbackup-binary']]
      self.logger.info("Server mode")
      command.extend(['--restrict', self.options['path']])
      command.append('--server')

      wrapper = self.createPythonScript(
        self.options['wrapper'],
        'slapos.recipe.librecipe.execute.execute',
        command)
      self.path_list.append(wrapper)

    return self.path_list
