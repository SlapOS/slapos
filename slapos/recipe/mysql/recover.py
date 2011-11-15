import sys
import os
import time
import subprocess

def import_remote_dump(kwargs):
  # Get data from kwargs
  lock_file = kwargs['lock_file']
  database = kwargs['database']
  mysql_binary = kwargs['mysql_binary']
  mysql_socket = kwargs['mysql_socket']
  duplicity_binary = kwargs['duplicity_binary']
  remote_backup = kwargs['remote_backup']
  local_directory = kwargs['local_directory']
  dump_name = kwargs['dump_name']
  zcat_binary = kwargs['zcat_binary']

  # The script start really here
  if os.path.exists(lock_file):
    sys.exit(127)

  while subprocess.call([mysql_binary, '--socket=%s' % mysql_socket,
                         '-u', 'root', '-e', 'use %s;' % database]) != 0:
    time.sleep(10)

  subprocess.check_call([duplicity_binary, 'restore', '--no-encryption',
                         remote_backup, local_directory])

  zcat = subprocess.Popen([zcat_binary, os.path.join(local_directory,
                                                     dump_name)],
                          stdout=subprocess.PIPE)
  mysql = subprocess.Popen([mysql_binary, '--socket=%s' % mysql_socket,
                            '-D', database, '-u', 'root'],
                           stdin=zcat.stdout)
  zcat.stdout.close()

  returncode = mysql.poll()

  if returncode == 0:
    open(lock_file, 'w').close() # Just a touch

  sys.exit(returncode)
