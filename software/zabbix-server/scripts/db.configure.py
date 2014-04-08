#!${:python_bin}

import os
import subprocess
import time

def startProcess(launch_args, env=None, cwd=None, stdout=subprocess.PIPE, shell=False):
  process = subprocess.Popen(launch_args, stdout=stdout,
              stderr=subprocess.STDOUT, env=env,
              cwd=cwd, shell=shell)
  result = process.communicate()[0]
  if process.returncode is None or process.returncode != 0:
    print "Failed to execute executable.\nThe error was: %s" % result
    return False
  return True

def dbtest(args):
  cmd = 'echo "connect %s;" | %s -h %s -P %s -u %s -p%s' % (args['mysql_db'],
        args['mysql_bin'], args['mysql_host'], args['mysql_port'],
        args['mysql_user'], args['mysql_password'])
  result = False
  while not result:
    time.sleep(5)
    result = startProcess(cmd, shell=True)

def install_script(args, script):
  cmd = 'cat %s | %s -h%s -P%s -u%s -p%s %s' % (script,
        args['mysql_bin'], args['mysql_host'], args['mysql_port'], 
        args['mysql_user'], args['mysql_password'], args['mysql_db'])
  os.system(cmd)

if __name__ == '__main__':
  args = {}
  args['mysql_bin'] = '${:mysql_bin}'
  args['mysql_host'] = '${:mysql_host}'
  args['mysql_port'] = '${:mysql_port}'
  args['mysql_user'] = '${:mysql_user}'
  args['mysql_password'] = '${:mysql_pwd}'
  args['mysql_db'] = '${:mysql_db}'
  scripts = []
  scripts.append('${:mysql_schema}')
  scripts.append('${:mysql_images}')
  scripts.append('${:mysql_data}')
  check_file = '${:installed_file}'
  #Check mysql status
  if os.path.exists(check_file):
    print "Database is configured. Exiting..."
    exit(0)
  dbtest(args)
  #Run all given sql files
  for script in scripts:
    install_script(args, script)
  with open(check_file, 'w') as f:
    f.write('installed')
  exit(0)
  