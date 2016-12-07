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
import subprocess
import sys
import textwrap
import urlparse

from slapos.recipe.librecipe import GenericSlapRecipe
from slapos.recipe.dropbear import KnownHostsFile
from slapos.recipe.notifier import Notify
from slapos.recipe.notifier import Callback
from slapos.recipe.librecipe import shlex


def promise(args):
  # Redirect output to /dev/null
  with open("/dev/null") as _dev_null:
    ssh = subprocess.Popen(
        [args['ssh_client'], '%(user)s@%(host)s' % args, '-p', '%(port)s' % args],
        stdin=subprocess.PIPE, stdout=_dev_null, stderr=None
    )

  # Rdiff Backup protocol quit command
  quitcommand = 'q' + chr(255) + chr(0) * 7

  ssh.stdin.write(quitcommand)
  ssh.stdin.flush()
  ssh.stdin.close()
  ssh.wait()

  if ssh.poll() is None:
    return 1
  if ssh.returncode != 0:
    sys.stderr.write("SSH Connection failed\n")
  return ssh.returncode



class Recipe(GenericSlapRecipe, Notify, Callback):
  def _options(self, options):
    options['rdiff-backup-data-folder'] = ""
    if 'slave-instance-list' in options:
      for slave in json.loads(options['slave-instance-list']):
        if slave['type'] == 'pull':
          options['rdiff-backup-data-folder'] = str(os.path.join(options['directory'], slave['name'], 'rdiff-backup-data'))

  def wrapper_push(self, remote_schema, local_dir, remote_dir, rdiff_wrapper_path):
    # Create a simple rdiff-backup wrapper that will push

    template = textwrap.dedent("""\
        #!/bin/sh
        #
        # Push data to a PBS *-import instance.
        #

        LC_ALL=C
        export LC_ALL
        RDIFF_BACKUP=%(rdiffbackup_binary)s
        $RDIFF_BACKUP \\
                --remote-schema %(remote_schema)s \\
                --restore-as-of now \\
                --force \\
                %(local_dir)s \\
                %(remote_dir)s
        """)

    template_dict = {
      'rdiffbackup_binary': shlex.quote(self.options['rdiffbackup-binary']),
      'remote_schema': shlex.quote(remote_schema),
      'remote_dir': shlex.quote(remote_dir),
      'local_dir': shlex.quote(local_dir)
    }

    return self.createFile(
      name=rdiff_wrapper_path,
      content=template % template_dict,
      mode=0o700
    )


  def wrapper_pull(self, remote_schema, local_dir, remote_dir, rdiff_wrapper_path, remove_backup_older_than):
    # Wrap rdiff-backup call into a script that checks consistency of backup
    # We need to manually escape the remote schema

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
        is_first_backup=$(test -d %(rdiff_backup_data)s || echo yes)
        RDIFF_BACKUP=%(rdiffbackup_binary)s

        TMPDIR=%(tmpdir)s
        BACKUP_DIR=%(local_dir)s
        CORRUPTED_MSG="^Warning:\ Computed\ SHA1\ digest\ of\ "
        CANTFIND_MSG="^Warning:\ Cannot\ find\ SHA1\ digest\ for\ file\ "
        CORRUPTED_FILE=$TMPDIR/$$.rdiff_corrupted
        CANTFIND_FILE=$TMPDIR/$$.rdiff_cantfind

        SUCCEEDED=false

        # not using --fix-corrupted can lead to an infinite loop
        # in case of manual changes to the backup repository.

        CORRUPTED_ARGS=""
        if [ "$1" = "--fix-corrupted" ]; then
            VERIFY=$($RDIFF_BACKUP --verify $BACKUP_DIR 2>&1 >/dev/null)
            echo "$VERIFY" | egrep "$CORRUPTED_MSG" | sed "s/$CORRUPTED_MSG//g" > $CORRUPTED_FILE

            # Sometimes --verify reports this spurious warning:
            echo "$VERIFY" | egrep "$CANTFIND_MSG" | sed "s/$CANTFIND_MSG\(.*\),/--always-snapshot\ '\\1'/g" > $CANTFIND_FILE

            # There can be too many files, better not to provide them through separate command line parameters
            CORRUPTED_ARGS="--always-snapshot-fromfile $CORRUPTED_FILE --always-snapshot-fromfile $CANTFIND_FILE"

            if [ -s "$CORRUPTED_FILE" -o -s "$CANTFIND_FILE" ]; then
                echo Retransmitting $(cat "$CORRUPTED_FILE" "$CANTFIND_FILE" | wc -l) corrupted/missing files
            else
                echo "No corrupted or missing files to retransmit"
            fi
        fi

        $RDIFF_BACKUP \\
                $CORRUPTED_ARGS \\
                --remote-schema %(remote_schema)s \\
                %(remote_dir)s \\
                $BACKUP_DIR

        RDIFF_BACKUP_STATUS=$?

        [ "$CORRUPTED_ARGS" ] && rm -f "$CORRUPTED_FILE" "$CANTFIND_FILE"

        if [ ! $RDIFF_BACKUP_STATUS -eq 0 ]; then
            # Check the backup, go to the last consistent backup, so that next
            # run will be okay.
            echo "Checking backup directory..."
            $RDIFF_BACKUP --check-destination-dir $BACKUP_DIR
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
            $RDIFF_BACKUP --remove-older-than %(remove_backup_older_than)s --force $BACKUP_DIR
        fi

        SUCCEEDED=true

        if [ -e %(backup_signature)s ]; then
          cd $BACKUP_DIR
          find -type f ! -name backup.signature ! -wholename "./rdiff-backup-data/*" -print0 | xargs -P4 -0 sha256sum  | LC_ALL=C sort -k 66 > ../proof.signature
          cmp backup.signature ../proof.signature || SUCCEEDED=false
          diff -ruw backup.signature ../proof.signature > ../backup.diff
          # XXX If there is a difference on the backup, we should publish the
          # failure and ask the equeue, re-run this script again,
          # instead do a push it to the clone.
        fi

        $SUCCEEDED || find $BACKUP_DIR -name rdiff-backup.tmp.* -exec rm -rf {} \;

        """)

    template_dict = {
      'rdiffbackup_binary': shlex.quote(self.options['rdiffbackup-binary']),
      'rdiff_backup_data': shlex.quote(os.path.join(local_dir, 'rdiff-backup-data')),
      'backup_signature': shlex.quote(os.path.join(local_dir, 'backup.signature')),
      'remote_schema': shlex.quote(remote_schema),
      'remote_dir': shlex.quote(remote_dir),
      'local_dir': shlex.quote(local_dir),
      'tmpdir': '/tmp',
      'remove_backup_older_than': shlex.quote(remove_backup_older_than)
    }

    return self.createFile(
      name=rdiff_wrapper_path,
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
    parsed_url = urlparse.urlparse(url)

    slave_type = entry['type']
    if not slave_type in ['pull', 'push']:
      raise ValueError('type parameter must be either pull or push.')

    slave_id = entry['notification-id']

    print 'Processing PBS slave %s with type %s' % (slave_id, slave_type)

    promise_path = os.path.join(self.options['promises-directory'], "ssh-to-%s" % slave_id)
    promise_dict = dict(ssh_client=self.options['sshclient-binary'],
                        user=parsed_url.username,
                        host=parsed_url.hostname,
                        port=parsed_url.port)
    promise = self.createPythonScript(promise_path,
                                      __name__ + '.promise',
                                      promise_dict)
    path_list.append(promise)

    # Create known_hosts file by default.
    # In some case, we don't want to create it (case where we share IP mong partitions)
    if not self.isTrueValue(self.options.get('ignore-known-hosts-file')):
      # Migration code: if known_hosts file contains entry with just IP, then it
      # is updated to use [IP]:port. It allows to share same IP among partitions
      if parsed_url.hostname in known_hosts_file:
        del known_hosts_file[parsed_url.hostname]
      known_hostname = "[%s]:%s" % (parsed_url.hostname, parsed_url.port)
      known_hosts_file[known_hostname] = entry['server-key'].strip()

    notifier_wrapper_path = os.path.join(self.options['wrappers-directory'], slave_id)
    rdiff_wrapper_path = notifier_wrapper_path + '_raw'

    # Create the rdiff-backup wrapper
    # It is useful to separate it from the notifier so that we can run it manually.

    remote_schema = '{ssh} -o "ConnectTimeout 300" -p %s {username}@{hostname}'.format(
              ssh=self.options['sshclient-binary'],
              username=parsed_url.username,
              hostname=parsed_url.hostname
            )
    remote_dir = '{port}::{path}'.format(port=parsed_url.port, path=parsed_url.path)
    local_dir = self.createDirectory(self.options['directory'], entry['name'])

    if slave_type == 'push':
      rdiff_wrapper = self.wrapper_push(remote_schema,
                                        local_dir,
                                        remote_dir,
                                        rdiff_wrapper_path)
    elif slave_type == 'pull':
      # XXX: only 3 increments is not enough by default.
      rdiff_wrapper = self.wrapper_pull(remote_schema,
                                        local_dir,
                                        remote_dir,
                                        rdiff_wrapper_path,
                                        entry.get('remove-backup-older-than', '3B'))

    path_list.append(rdiff_wrapper)

    # Create notifier wrapper
    notifier_wrapper = self.createNotifier(
        notifier_binary=self.options['notifier-binary'],
        wrapper=notifier_wrapper_path,
        executable=rdiff_wrapper,
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
