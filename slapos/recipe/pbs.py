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

from __future__ import print_function

import json
import os
import subprocess
import sys
import textwrap
from six.moves.urllib.parse import urlparse

from slapos.recipe.librecipe import GenericSlapRecipe
from slapos.recipe.dropbear import KnownHostsFile
from slapos.recipe.notifier import Notify
from slapos.recipe.notifier import Callback
from slapos.recipe.librecipe import shlex


def promise(ssh_client, user, host, port):
  # Redirect output to /dev/null
  with open(os.devnull, 'wb') as _dev_null:
    ssh = subprocess.Popen(
        (ssh_client, '%s@%s' % (user, host), '-p', str(port)),
        stdin=subprocess.PIPE, stdout=_dev_null, universal_newlines=True)
  ssh.communicate('q' + chr(255) + chr(0) * 7)
  if ssh.returncode:
    sys.stderr.write("SSH Connection failed\n")
  return ssh.returncode


class Recipe(GenericSlapRecipe, Notify, Callback):
  def _options(self, options):
    options['rdiff-backup-data-folder'] = ""
    if 'slave-instance-list' in options:
      for slave in options['slave-instance-list']:
        if slave['type'] == 'pull':
          options['rdiff-backup-data-folder'] = str(os.path.join(options['directory'], slave['name'], 'rdiff-backup-data'))

  def wrapper_push(self, remote_schema, local_dir, restic_wrapper_path):
    # Create a simple rdiff-backup wrapper that will push

    template = textwrap.dedent("""\
        #!/bin/sh
        #
        # Push data to a PBS *-import instance.
        #

        LC_ALL=C
        export LC_ALL
        RESTIC=%(restic_binary)s
        RESTIC_REST_SERVER=%(restic_rest_server_binary)s
        RESTIC_REPOSITORY=%(restic_repository)s
        REMOTE_SOCKET=%(remote_socket)s
        LOCAL_SOCKET=%(local_socket)s

        # start rest-server
        $RESTIC_REST_SERVER --listen unix:$LOCAL_SOCKET --no-auth --path=$RESTIC_REPOSITORY &
        RESTIC_REST_SERVER_PID=$!
        START_TIME=$(date +%%s)
        TIMEOUT="10"
        while true; do
            test -S $LOCAL_SOCKET && break
            ELAPSED=$(($(date +%%s) - START_TIME))
            if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
                echo "rest-server socket did not appear in $TIMEOUT seconds."
                exit 1
            fi
            sleep 0.1
        done

        %(remote_schema)s -R $REMOTE_SOCKET:$LOCAL_SOCKET restore

        # stop rest-server
        kill $RESTIC_REST_SERVER_PID
        wait $RESTIC_REST_SERVER_PID
        """)

    local_socket = os.path.join(
      os.path.dirname(local_dir.rstrip('/')), 'restick.sock'
    )
    template_dict = {
      'restic_binary': shlex.quote(self.options['restic-binary']),
      'restic_rest_server_binary': shlex.quote(self.options['restic-rest-server-binary']),
      'remote_schema': remote_schema,
      'restic_repository': shlex.quote(os.path.join(local_dir, 'restic')),
      'local_socket': shlex.quote(local_socket),
      'remote_socket': shlex.quote(os.path.join(local_dir, 'restic.sock')),
    }

    return self.createFile(
      name=restic_wrapper_path,
      content=template % template_dict,
      mode=0o700
    )


  def wrapper_pull(self, remote_schema, local_dir, restic_wrapper_path, remove_backup_older_than):
    # Wrap rdiff-backup call into a script that checks consistency of backup
    # We need to manually escape the remote schema

    # BBB translate rdiff-backup's --remove-older-than parameter to restic's forget policy.
    remove_backup_older_than = remove_backup_older_than.lower()
    if remove_backup_older_than.endswith('b'):
      keep_args = ('--keep-last ', remove_backup_older_than[:-1])
    else:
      if remove_backup_older_than.endswith('w'):
        remove_backup_older_than = '%sd' % (int(remove_backup_older_than[:-1]) * 7)
      keep_args = ('--keep-within', remove_backup_older_than)

    template = textwrap.dedent("""\
        #!/bin/sh
        #
        # Pull data from a PBS *-export instance.
        #

        sigint()
        {
          exit 1
        }

        trap sigint INT  # we can CTRL-C for ease of debugging

        LC_ALL=C
        export LC_ALL
        is_first_backup=$(test -d %(restic_repository)s || echo yes)
        RESTIC=%(restic_binary)s
        RESTIC_REST_SERVER=%(restic_rest_server_binary)s
        BACKUP_DIR=%(local_dir)s
        RESTIC_REPOSITORY=%(restic_repository)s
        REMOTE_SOCKET=%(remote_socket)s
        LOCAL_SOCKET=%(local_socket)s

        test -d $RESTIC_REPOSITORY || $RESTIC init --insecure-no-password -r $RESTIC_REPOSITORY

        # import existing rdiff-backup if exists.
        if [ -d %(rdiff_backup_data)s ]; then
            cd $BACKUP_DIR
            $RESTIC backup . --insecure-no-password -r $RESTIC_REPOSITORY \\
                --exclude=rdiff-backup-data --exclude=restic
        fi

        # start rest-server
        $RESTIC_REST_SERVER --listen unix:$LOCAL_SOCKET --no-auth --path=$RESTIC_REPOSITORY &
        RESTIC_REST_SERVER_PID=$!
        START_TIME=$(date +%%s)
        TIMEOUT="10"
        while true; do
            test -S $LOCAL_SOCKET && break
            ELAPSED=$(($(date +%%s) - START_TIME))
            if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
                echo "rest-server socket did not appear in $TIMEOUT seconds."
                exit 1
            fi
            sleep 0.1
        done

        %(remote_schema)s -R $REMOTE_SOCKET:$LOCAL_SOCKET backup
        RESTIC_STATUS=$?

        if [ ! $RESTIC_STATUS -eq 0 ]; then
            # Check the backup, go to the last consistent backup, so that next
            # run will be okay.
            echo "Checking backup directory..."
            $RESTIC check --insecure-no-password -r $RESTIC_REPOSITORY
            if [ ! $? -eq 0 ]; then
                # Here, two possiblities:
                if [ is_first_backup ]; then
                    continue
                    # The first backup failed, and check-destination as well.
                    # we may want to remove the backup.
                else
                    continue
                    # The backup command has failed, while transferring an increment, and check-destination as well.
                    # XXX We may need to publish the failure and ask the the equeue, re-run this script again,
                    # instead do a push to the clone.
                fi
            fi
        else
            # Everything's okay, cleaning up...
            $RESTIC forget %(keep_args)s --insecure-no-password -r $RESTIC_REPOSITORY
        fi

        # stop rest-server
        kill $RESTIC_REST_SERVER_PID
        wait $RESTIC_REST_SERVER_PID
        """)

    local_socket = os.path.join(
      os.path.dirname(local_dir.rstrip('/')), 'restick.sock'
    )
    template_dict = {
      'restic_binary': shlex.quote(self.options['restic-binary']),
      'restic_rest_server_binary': shlex.quote(self.options['restic-rest-server-binary']),
      'rdiff_backup_data': shlex.quote(os.path.join(local_dir, 'rdiff-backup-data')),
      'remote_schema': remote_schema,
      'local_dir': shlex.quote(local_dir),
      'restic_repository': shlex.quote(os.path.join(local_dir, 'restic')),
      'local_socket': shlex.quote(local_socket),
      'remote_socket': shlex.quote(os.path.join(local_dir, 'restic.sock')),
      'keep_args': ' '.join(shlex.quote(e) for e in keep_args),
    }

    return self.createFile(
      name=restic_wrapper_path,
      content=template % template_dict,
      mode=0o700
    )


  def wrapper_restic(self, restic_wrapper_path, restic_binary_path, local_dir):
    template = textwrap.dedent("""\
        #!/bin/sh
        RESTIC=%(restic_binary)s
        BACKUP_DIR=%(local_dir)s
        LOCAL_SOCKET=%(socket_path)s
        case "$SSH_ORIGINAL_COMMAND" in
            backup)
                cd $BACKUP_DIR
                $RESTIC backup --insecure-no-password -r rest:http+unix:$LOCAL_SOCKET: .
            ;;
            restore)
                $RESTIC restore latest --insecure-no-password -r rest:http+unix:$LOCAL_SOCKET: -t $BACKUP_DIR
            ;;
            *)
                echo "Unexpected SSH_ORIGINAL_COMMAND: $SSH_ORIGINAL_COMMAND"
            ;;
        esac
     """)
    socket_path = os.path.join(
      os.path.dirname(local_dir.rstrip('/')), 'restick.sock'
    )
    template_dict = {
      'restic_binary': shlex.quote(restic_binary_path),
      'local_dir': shlex.quote(local_dir),
      'socket_path': shlex.quote(socket_path),
    }

    return self.createFile(
      name=restic_wrapper_path,
      content=template % template_dict,
      mode=0o700
    )


  def add_slave(self, entry, known_hosts_file):
    path_list = []

    url = entry.get('url')
    if not url:
      return path_list
      # It used to raise an error if url was not defined.
      # This behavior has been removed to accelerate deployment of the
      # Software Release. The buildout, instead of failing, can process
      # other sections, which will return parameters to the main instance faster
    parsed_url = urlparse(url)

    slave_type = entry['type']
    if not slave_type in ['pull', 'push']:
      raise ValueError('type parameter must be either pull or push.')

    slave_id = entry['notification-id']

    print('Processing PBS slave %s with type %s' % (slave_id, slave_type))

    path_list.append(self.createPythonScript(
      os.path.join(self.options['promises-directory'], "ssh-to-%s" % slave_id),
      __name__ + '.promise',
      (self.options['sshclient-binary'],
       parsed_url.username, parsed_url.hostname, parsed_url.port)))

    # Create known_hosts file
    known_hostname = "[%s]:%s" % (parsed_url.hostname, parsed_url.port)
    known_hosts_file[known_hostname] = entry['server-key'].strip()

    notifier_wrapper_path = os.path.join(self.options['wrappers-directory'], slave_id)
    restic_wrapper_path = notifier_wrapper_path + '_raw'

    # Create the rdiff-backup wrapper
    # It is useful to separate it from the notifier so that we can run it manually.

    remote_schema = ('{ssh} '
              '-o "ConnectTimeout 300" '
              '-o "ServerAliveCountMax 10" '
              '-o "ServerAliveInterval 30" '
              '-p {port} '
              '{username}@{hostname}').format(
              ssh=self.options['sshclient-binary'],
              port=parsed_url.port,
              username=parsed_url.username,
              hostname=parsed_url.hostname
            )
    local_dir = self.createDirectory(self.options['directory'], entry['name'])

    if slave_type == 'push':
      restic_wrapper = self.wrapper_push(remote_schema,
                                        local_dir,
                                        restic_wrapper_path)
    elif slave_type == 'pull':
      # XXX: only 3 increments is not enough by default.
      restic_wrapper = self.wrapper_pull(remote_schema,
                                        local_dir,
                                        restic_wrapper_path,
                                        entry.get('remove-backup-older-than', '3B'))

    path_list.append(restic_wrapper)

    # Create notifier wrapper
    notifier_wrapper = self.createNotifier(
        notifier_binary=self.options['notifier-binary'],
        wrapper=notifier_wrapper_path,
        executable=restic_wrapper,
        log=os.path.join(self.options['feeds'], entry['notification-id']),
        title=entry.get('title', slave_id),
        notification_url=entry['notify'] or '',
        feed_url='%s/get/%s' % (self.options['notifier-url'], entry['notification-id']),
        max_run=self.options.get('pull-push-maximum-run', 1),
        pidfile=os.path.join(self.options['run-directory'], '%s.pid' % slave_id),
        instance_root_name=self.options.get('instance-root-name', None),
        log_url=self.options.get('log-url', None),
        status_item_directory=self.options.get('status-item-directory', None)
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
      slaves = self.options['slave-instance-list']
      known_hosts = KnownHostsFile(self.options['known-hosts'])
      with known_hosts:
        for slave in slaves:
          path_list.extend(self.add_slave(slave, known_hosts))
    else:
      self.logger.info("Server mode")

      wrapper = self.wrapper_restic(
        self.options['wrapper'],
        self.options['restic-binary'],
        self.options['path'],
      )
      path_list.append(wrapper)

    return path_list
