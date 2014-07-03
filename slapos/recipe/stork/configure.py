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
import subprocess
import time

def submitJob(args):
  """Run stork_submit (if needed) for job deployment"""
  time.sleep(10)

  # '-a', "log = out.log", '-a', "error = error.log",
  server_info=args['stork_server']+':'+args['server_port']
  launch_args = [args['submit'],server_info, args['submit_file']]
  process = subprocess.Popen(launch_args, stdout=subprocess.PIPE,
              stderr=subprocess.STDOUT, cwd=args['datadir'])
  result = process.communicate()[0]
  if process.returncode is None or process.returncode != 0:
    print "Failed to execute stork_submit.\nThe error was: %s" % result

def storkStart(args):
    """Start Stork """
    proc_args = [args['start_bin'],
                '-p', args['port'],
                '-c', args['configfile']
              ]
    
    process = subprocess.Popen(proc_args, stderr=subprocess.STDOUT,
                                stdout=subprocess.PIPE)
    time.sleep(3)
    print "\n\nStork Server started with pid %s " % process.pid
    with open(args['pid'], 'w') as f:
      f.write(str(process.pid))
    result = process.communicate()[0]
    if process.returncode is None or process.returncode != 0:
      print "Failed to start Stork Server.\nThe error was: %s" % result

def checkDownloadStatus(args):
  "Check if all files have been downloaded! "
  job_count = len(args['dest_list'])
  os.chdir(args['cwd'])

  while job_count > 0:
    print "Check if %s files have been downloaded!" % job_count
    for filename in args['dest_list']:
      log_name = "%s.err" % filename
      destination = args['dest_list'][filename]
      if os.path.exists(destination):
        job_count -= 1
        continue
      if os.path.exists(destination + '_part') and os.path.exists(log_name):
        with open(log_name, 'r') as log_file:
          if not log_file.readline().startswith('SUCCESS'):
            with open(filename + '.out', 'r') as out_file:
              if not out_file.readline().startswith('SUCCESS'):
                continue
        job_count -= 1
        time.sleep(2)
        os.rename(destination + '_part', destination)
        print "File %s is correctly downloaded!" % destination
      else:
        print "ERROR!! Check if destination and log_files exist... %s" % destination
    
    time.sleep(5)
    