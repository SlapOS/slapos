#!/usr/bin/python

import os
import subprocess
import sys

def runPromise(promise_path):
  promise_relative_path = promise_path.replace(os.path.expanduser('~'), '~')
  print 'Running promise %s...' % promise_relative_path
  promise_process = subprocess.Popen(promise_path, stderr=subprocess.PIPE)
  stdout, stderr = promise_process.communicate()
  return_code = promise_process.returncode
  if return_code == 0:
    print 'Success.'
    return True
  else:
    sys.stderr.write('Failure while running promise %s. %s\n' % (promise_relative_path, stderr))

def getPromisePathListFromPartitionPath(partition_path):
  promise_directory_path = os.path.join(partition_path, 'etc/promise')
  try:
    promise_name_list = os.listdir(promise_directory_path)
    return [os.path.join(promise_directory_path, promise_name) for promise_name in promise_name_list]
  except OSError:
    return []

def main():
  # XXX hardcoded
  partition_root_path = os.path.expanduser('~/srv/runner/instance')
  success = True
  for partition_name in os.listdir(partition_root_path):
    partition_path = os.path.join(partition_root_path, partition_name)
    for promise_path in getPromisePathListFromPartitionPath(partition_path):
      result = runPromise(promise_path)
      if not result:
        success = False
  if not success:
    sys.exit(1)

if __name__ == '__main__':
  main()

