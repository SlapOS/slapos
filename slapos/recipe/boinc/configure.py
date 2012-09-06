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
import sys
import subprocess
import time
import shutil

def checkMysql(args):
  sys.path += args['python_path'].split(':')
  import MySQLdb
  #Sleep until mysql server becomes available
  while True:
    try:
      conn = MySQLdb.connect(host = args['mysql_host'],
                          user = args['mysql_user'],
                          port = int(args['mysql_port']),
                          passwd = args['mysql_password'],
                          db = args['database'])
      conn.close()
      print "Successfully connect to MySQL database... "
      file = open(args['file_status'], 'w')
      file.write("starting")
      file.close()
      break
    except Exception, ex:
      print "The result is: \n" + ex.message
      print "Could not connect to MySQL database... sleep for 2 secondes"
      time.sleep(2)


def services(args):
  #Sleep until file 'boinc_project'.readme exist
  while True:
    print "Search for file %s..." % args['readme']
    if not os.path.exists(args['readme']):
      print "File not found... sleep for 3 secondes"
      time.sleep(3)
    else:
      break

  topath = os.path.join(args['installroot'], 'html/ops/.htpasswd')
  print "Generating .htpasswd file... File=%s" % topath
  passwd = open(args['passwd'], 'r').read()
  p_htpasswd = subprocess.Popen([args['htpasswd'], '-b', '-c', topath,
        args['username'], passwd],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  result = p_htpasswd.communicate()[0]
  if p_htpasswd.returncode is None or p_htpasswd.returncode != 0:
    print "Failed to create file %s.\nThe error was: %s" % (topath, result)
    return

  print "Running xadd script..."
  env = os.environ
  env['PATH'] = args['environment']['PATH']
  env['PYTHONPATH'] = args['environment']['PYTHONPATH']
  env['PYTHON'] = args['environment']['PYTHON']
  p_xadd = subprocess.Popen([args['xadd']], stdout=subprocess.PIPE,
          stderr=subprocess.STDOUT, env=env)
  result = p_xadd.communicate()[0]
  if p_xadd.returncode is None or p_xadd.returncode != 0:
    print "Failed to execute bin/xadd.\nThe error was: %s" % result
    return
  print "Update files and directories permissions..."
  upload = os.path.join(args['installroot'], 'upload')
  inc = os.path.join(args['installroot'], 'html/inc')
  languages = os.path.join(args['installroot'], 'html/languages')
  compiled = os.path.join(args['installroot'], 'html/languages/compiled')
  user_profile = os.path.join(args['installroot'], 'html/user_profile')
  forum_file = os.path.join(args['installroot'], 'html/ops/create_forums.php')
  project_inc = os.path.join(args['installroot'], 'html/project/project.inc')
  cmd = "chmod 02770 -R %s %s, %s %s %s" % (upload, inc,
              languages, compiled, user_profile)
  os.system("chmod g+w -R " + args['installroot'])
  os.system(cmd)
  os.system("chmod o+x " + inc)
  os.system("chmod -R o+r " + inc)
  os.system("chmod o+x " + languages)
  os.system("chmod o+x " + compiled)
  os.system("sed -i '/remove the die/d' %s" % forum_file)
  subprocess.Popen(["sed -i 's#REPLACE WITH PROJECT NAME#%s#' %s" % (args['fullname'],
      project_inc)], shell=True, stdout=subprocess.PIPE).communicate()[0]
  subprocess.Popen(["sed -i 's#REPLACE WITH COPYRIGHT HOLDER#%s#' %s" % (args['copyright'],
      project_inc)], shell=True, stdout=subprocess.PIPE).communicate()[0]

  #Execute php create_forum.php...
  print "Boinc Forum: Execute php create_forum.php..."
  p_forum = subprocess.Popen(["php", forum_file], stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT, env=env, cwd=os.path.join(args['installroot'],
      'html/ops'))
  result = p_forum.communicate()[0]
  if p_forum.returncode is None or p_forum.returncode != 0:
    print "Failed to execute bin/xadd.\nThe error was: %s" % result
    return

  status = open(args['service_status'], "w")
  status.write("started")
  status.close()

def deployApp(args):
  print "Cheking if needed to install %s..." % args['appname']
  if os.path.exists(os.path.join(args['installroot'], "."+args['appname'])):
    print args['appname'] + " is already installed in this Boinc instance... skipped"
    return
  #Sleep until file .start_service exist (Mark the end of boinc configuration)
  while True:
    print "Search for file %s..." % args['service_status']
    if not os.path.exists(args['service_status']):
      print "File not found... sleep for 3 secondes"
      time.sleep(3)
    else:
      break

  print "sleeps for 30 seconds while waiting for the end of the execution of boinc_start"
  time.sleep(30)

  print "setup directories..."
  args['inputfile'] = os.path.join(args['installroot'], 'download',
                        args['appname']+'_input')
  base_app = os.path.join(args['installroot'], 'apps', args['appname'])
  base_app_version = os.path.join(base_app, args['version'])
  args['templates'] = os.path.join(args['installroot'], 'templates')
  if not os.path.exists(base_app):
    os.mkdir(base_app)
  if os.path.exists(base_app_version):
    shutil.rmtree(base_app_version)
  os.mkdir(base_app_version)
  os.mkdir(args['application'])
  if not os.path.exists(args['templates']):
    os.mkdir(args['templates'])
  shutil.copy(args['t_result'], os.path.join(args['templates'],
          args['appname']+'_result'))
  shutil.copy(args['t_wu'], os.path.join(args['templates'],
          args['appname']+'_wu'))
  shutil.copy(args['t_input'], args['inputfile'])
  shutil.copy(args['binary'], os.path.join(args['application'],
        args['binary_name']))

  print "Adding '" + args['appname'] + "' to project.xml..."
  print "Adding deamon for application to config.xml..."
  project_xml = os.path.join(args['installroot'], 'project.xml')
  config_xml = os.path.join(args['installroot'], 'config.xml')
  sed_args = [args['bash'], args['appname'], args['installroot']]
  sed = subprocess.Popen(sed_args, stderr=subprocess.STDOUT,
              stdout=subprocess.PIPE)
  result = sed.communicate()[0]
  print result

  print "Running xadd script..."
  env = os.environ
  env['PATH'] = args['environment']['PATH']
  env['PYTHONPATH'] = args['environment']['PYTHONPATH']
  env['PYTHON'] = args['environment']['PYTHON']
  p_xadd = subprocess.Popen([os.path.join(args['installroot'], 'bin/xadd')],
          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
  result = p_xadd.communicate()[0]
  if p_xadd.returncode is None or p_xadd.returncode != 0:
    print "Failed to execute bin/xadd.\nThe error was: %s" % result
    return

  print "Sign the application binary..."
  sign = os.path.join(args['installroot'], 'bin/sign_executable')
  privateKeyFile = os.path.join(args['installroot'], 'keys/code_sign_private')
  output = open(os.path.join(args['application'], args['binary_name']+'.sig'), 'w')
  p_sign = subprocess.Popen([sign, os.path.join(args['application'],
          args['binary_name']), privateKeyFile], stdout=output,
          stderr=subprocess.STDOUT)
  result = p_sign.communicate()[0]
  if p_sign.returncode is None or p_sign.returncode != 0:
    print "Failed to execute bin/sign_executable.\nThe error was: %s" % result
    return
  output.close()

  print "Running script bin/update_versions..."
  updt_version = os.path.join(args['installroot'], 'bin/update_versions')
  p_version = subprocess.Popen([updt_version], stdout=subprocess.PIPE,
          stderr=subprocess.STDOUT, stdin=subprocess.PIPE, env=env,
          cwd=args['installroot'])
  p_version.stdin.write('y\ny\n')
  result = p_version.communicate()[0]
  p_version.stdin.close()
  if p_version.returncode is None or p_version.returncode != 0:
    print "Failed to execute bin/update_versions.\nThe error was: %s" % result
    return

  print "Fill the database... calling bin/create_work..."
  create_wu(args, env)

  print "Restart Boinc..."
  binstart = os.path.join(args['installroot'], 'bin/start')
  binstop = os.path.join(args['installroot'], 'bin/stop')
  os.system(binstop)
  os.system(binstart)

  print "Boinc Application deployment is done... writing end signal file..."
  sfile = open(os.path.join(args['installroot'], "."+args['appname']), 'w')
  sfile.write("done")
  sfile.close()

def create_wu(args, env):
  count = int(args['wu_number'])
  launch_args = [os.path.join(args['installroot'], 'bin/create_work'),
        '--appname', args['appname'], '--wu_name', args['wu_name'],
        '--wu_template', os.path.join(args['templates'], args['appname'] + '_wu'),
        '--result_template', os.path.join(args['templates'], args['appname'] + '_result'),
        args['inputfile']]
  for i in range(count - 1):
    print "Creating project wroker num %s..." % args['wu_number']
    launch_args[4] = args['wu_name']+str(i+1)
    process = subprocess.Popen(launch_args, stdout=subprocess.PIPE,
              stderr=subprocess.STDOUT, env=env,
              cwd=args['installroot'])
    process.communicate()[0]

    