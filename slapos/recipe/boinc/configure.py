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
  cmd = "chmod 02770 -R %s %s, %s %s %s" % (upload, inc,
              languages, compiled, user_profile)
  os.system("chmod g+w -R " + args['installroot'])
  os.system(cmd)
  os.system("chmod o+x " + inc)
  os.system("chmod -R o+r " + inc)
  os.system("chmod o+x " + languages)
  os.system("chmod o+x " + compiled)

  status = open(args['service_status'], "w")
  status.write("started")
  status.close()
  