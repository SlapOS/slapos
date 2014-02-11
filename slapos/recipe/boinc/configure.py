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
import re
import filecmp

from lock_file import LockFile

def checkMysql(args):
  sys.path += args['environment']['PYTHONPATH'].split(':')
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
      if args.has_key('file_status'):
        writeFile(args['file_status'], "starting")
      break
    except Exception, ex:
      print "The result is: \n" + ex.message
      print "Could not connect to MySQL database... sleep for 2 secondes"
      time.sleep(2)


def checkFile(file, stime):
  """Loop until 'file' is created (exist)"""
  while True:
    print "Search for file %s..." % file
    if not os.path.exists(file):
      print "File not found... sleep for %s secondes" % stime
      time.sleep(stime)
    else:
      break


def restart_boinc(args):
  """Stop (if currently is running state) and start all Boinc service"""
  if args['drop_install']:
    checkFile(args['service_status'], 3)
  else:
    checkMysql(args)
  print "Restart Boinc..."
  env = os.environ
  env['PATH'] = args['environment']['PATH']
  env['PYTHONPATH'] = args['environment']['PYTHONPATH']
  binstart = os.path.join(args['installroot'], 'bin/start')
  binstop = os.path.join(args['installroot'], 'bin/stop')
  os.system(binstop)
  os.system(binstart)
  writeFile(args['start_boinc'], "started")
  print "Done."


def check_installRequest(args):
  print "Cheking if needed to install %s..." % args['appname']
  install_request_file = os.path.join(args['home_dir'],
                  '.install_' + args['appname'] + args['version'])
  if not os.path.exists(install_request_file):
    print "No install or update request for %s version %s..." % (
                args['appname'], args['version'])
    return False
  os.unlink(install_request_file)
  return True

def copy_file(source, dest):
  """"Copy file with source to dest with auto replace
      return True if file has been copied and dest ha been replaced
  """
  result = False
  if source and os.path.exists(source):
    if os.path.exists(dest):
      if filecmp.cmp(dest, source):
        return False
      os.unlink(dest)
    result = True
    shutil.copy(source, dest)
  return result


def startProcess(launch_args, env=None, cwd=None, stdout=subprocess.PIPE):
  process = subprocess.Popen(launch_args, stdout=stdout,
              stderr=subprocess.STDOUT, env=env,
              cwd=cwd)
  result = process.communicate()[0]
  if process.returncode is None or process.returncode != 0:
    print "Failed to execute executable.\nThe error was: %s" % result
    return False
  return True

def makeProject(args):
  """Run BOINC make_project script but once only"""
  #Wait for DateBase initialization...
  checkFile(args['make_sig'], 3)
  print "Cheking if needed to run BOINC make_project..."
  if os.path.exists(args['request_file']):
    env = os.environ
    env['PATH'] = args['env']['PATH']
    env['PYTHONPATH'] = args['env']['PYTHONPATH']
    if startProcess(args['launch_args'], env=env):
      os.unlink(args['request_file'])
    print "Finished running BOINC make_projet...Ending"
  else:
    print "No new request for make_project. Exiting..."


def services(args):
  """This function configure a new installed boinc project instance"""
  print "Checking if needed to install or reinstall Boinc-server..."
  if not args['drop_install']:
    print "Not need to install Boinc-server...skipped"
    return
  #Sleep until file 'boinc_project'.readme exist
  checkFile(args['readme'], 3)

  topath = os.path.join(args['installroot'], 'html/ops/.htpasswd')
  print "Generating .htpasswd file... File=%s" % topath
  passwd = open(args['passwd'], 'r').read()
  htpwd_args = [args['htpasswd'], '-b', '-c', topath, args['username'], passwd]
  if not startProcess(htpwd_args):
    return

  print "execute script xadd..."
  env = os.environ
  env['PATH'] = args['environment']['PATH']
  env['PYTHONPATH'] = args['environment']['PYTHONPATH']
  if not startProcess([os.path.join(args['installroot'], 'bin/xadd')], env):
    return
  print "Update files and directories permissions..."
  upload = os.path.join(args['installroot'], 'upload')
  inc = os.path.join(args['installroot'], 'html/inc')
  languages = os.path.join(args['installroot'], 'html/languages')
  compiled = os.path.join(args['installroot'], 'html/languages/compiled')
  user_profile = os.path.join(args['installroot'], 'html/user_profile')
  forum_file = os.path.join(args['installroot'], 'html/ops/create_forums.php')
  project_inc = os.path.join(args['installroot'], 'html/project/project.inc')
  cmd = "chmod 02700 -R %s %s, %s %s %s" % (upload, inc,
              languages, compiled, user_profile)
  os.system("chmod g+w -R " + args['installroot'])
  os.system(cmd)
  os.system("chmod 700 %s" % os.path.join(args['installroot'], 'keys'))
  os.system("chmod o+x " + inc)
  os.system("chmod -R o+r " + inc)
  os.system("chmod o+x " + languages)
  os.system("chmod o+x " + compiled)
  sed_args = [args['sedconfig']]
  startProcess(sed_args)

  #Execute php create_forum.php...
  print "Boinc Forum: Execute php create_forum.php..."
  cwd = os.path.join(args['installroot'], 'html/ops')
  if not startProcess(["php", forum_file], env, cwd):
    return

  writeFile(args['service_status'], "started")

def deployApp(args):
  """Deploy Boinc App with lock"""
  print "Asking to enter in execution with lock mode..."
  with LockFile(args['lockfile'], wait=True):
    print "acquire the lock file..."
    deployManagement(args)
  print "Exit execution with lock..."

def deployManagement(args):
  """Fully deploy or redeploy or update a BOINC application using existing BOINC instance"""
  if not check_installRequest(args):
    return
  token = os.path.join(args['installroot'], "." + args['appname'] + args['version'])
  newInstall = False
  if os.path.exists(token):
    args['previous_wu'] = int(open(token, 'r').read().strip())
    if args['previous_wu'] < args['wu_number']:
      print args['appname'] + " Work units will be updated from %s to %s" % (
                args['previous_wu'], args['wu_number'])
  else:
    args['previous_wu'] = 0
    newInstall = True
  #Sleep until file .start_boinc exist (File indicate that BOINC has been started)
  checkFile(args['start_boinc'], 3)
  env = os.environ
  env['PATH'] = args['environment']['PATH']
  env['PYTHONPATH'] = args['environment']['PYTHONPATH']

  print "setup directories..."
  numversion = args['version'].replace('.', '')
  args['inputfile'] = os.path.join(args['installroot'], 'download',
                        args['appname'] + numversion + '_input')
  base_app = os.path.join(args['installroot'], 'apps', args['appname'])
  base_app_version = os.path.join(base_app, args['version'])
  args['templates'] = os.path.join(args['installroot'], 'templates')
  t_result = os.path.join(args['templates'],
                          args['appname'] + numversion + '_result')
  t_wu = os.path.join(args['templates'],
                          args['appname'] + numversion + '_wu')
  binary_name = args['appname'] +"_"+ args['version'] +"_"+ \
          args['platform'] +  args['extension']
  binary = os.path.join(args['application'], binary_name)
  signBin = False
  if not os.path.exists(base_app):
    os.mkdir(base_app)
  if newInstall:
    if os.path.exists(base_app_version):
      shutil.rmtree(base_app_version)
    os.mkdir(base_app_version)
    os.mkdir(args['application'])
  if not os.path.exists(args['templates']):
    os.mkdir(args['templates'])
  copy_file(args['t_result'], t_result)
  copy_file(args['t_wu'], t_wu)
  signBin = copy_file(args['binary'], binary)
  if args['t_input']:
    if os.path.exists(args['inputfile']):
      os.unlink(args['inputfile'])
    os.symlink(args['t_input'], args['inputfile'])

  project_xml = os.path.join(args['installroot'], 'project.xml')
  findapp = re.search("<name>(%s)</name>" % args['appname'],
                open(project_xml, 'r').read())
  if not findapp:
    print "Adding '" + args['appname'] + "' to project.xml..."
    print "Adding deamon for application to config.xml..."
    sed_args = [args['bash'], args['appname'], args['installroot']]
    startProcess(sed_args)

  if signBin:
    print "Sign the application binary..."
    sign = os.path.join(args['installroot'], 'bin/sign_executable')
    privateKeyFile = os.path.join(args['installroot'], 'keys/code_sign_private')
    output = open(binary + '.sig', 'w')
    p_sign = subprocess.Popen([sign, binary, privateKeyFile], stdout=output,
            stderr=subprocess.STDOUT)
    result = p_sign.communicate()[0]
    if p_sign.returncode is None or p_sign.returncode != 0:
      print "Failed to execute bin/sign_executable.\nThe error was: %s" % result
      return
    output.close()

  print "execute script xadd..."

  if not startProcess([os.path.join(args['installroot'], 'bin/xadd')], env):
    return
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
  writeFile(token, str(args['wu_number']))


def create_wu(args, env):
  """Create or update number of work unit for an existing boinc application"""
  numversion = args['version'].replace('.', '')
  t_result = "templates/" + args['appname'] + numversion + '_result'
  t_wu = "templates/" + args['appname'] + numversion + '_wu'
  launch_args = [os.path.join(args['installroot'], 'bin/create_work'),
        '--appname', args['appname'], '--wu_name', '',
        '--wu_template', t_wu, '--result_template', t_result,
        '--min_quorum', '1',  '--target_nresults', '1',
        args['appname'] + numversion + '_input']
  for i in range(args['previous_wu'], args['wu_number']):
    print "Creating project wroker %s..." % str(i+1)
    launch_args[4] = args['appname'] + str(i+1) + numversion + '_nodelete'
    startProcess(launch_args, env, args['installroot'])


def runCmd(args):
  """Wait for Boinc Client started and run boinc cmd"""
  client_config = os.path.join(args['installdir'], 'client_state.xml')
  checkFile(client_config, 5)
  time.sleep(10)
  #Scan client state xml to find client ipv4 adress
  host = re.search("<ip_addr>([\w\d\.:]+)</ip_addr>",
                open(client_config, 'r').read()).group(1)
  args['base_cmd'][2] = host + ':' + args['base_cmd'][2]
  print "Run boinccmd with host at %s " % args['base_cmd'][2]
  project_args = args['base_cmd'] + ['--project_attach', args['project_url'],
                      args['key']]
  startProcess(project_args, cwd=args['installdir'])
  if args['cc_cmd'] != '':
    #Load or reload cc_config file
    startProcess(args['base_cmd'] + [args['cc_cmd']], cwd=args['installdir'])


def writeFile(file, content):
  f = open(file, 'w')
  f.write(content)
  f.close()
