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

def runProcess(args, file):
  filename = file.split('/')[-1:][0]
  stdout_file = open(os.path.join(args['bg_log'], filename + ".log"), 'w')
  process = subprocess.Popen(file, stdout=stdout_file,
          stderr=subprocess.STDOUT)
  fp = open(os.path.join(args['bg_pid'], filename + '.pid'), 'w')
  fp.write(str(process.pid))
  fp.close()
  return process.pid

def launchScript(args):
  print "Sleep for a few second..."
  time.sleep(10)
  pid_list = []
  bg_pid = os.path.join(args['bg_base'], 'pid')
  bg_log = os.path.join(args['bg_base'], 'log')
  args['bg_pid'] = bg_pid
  args['bg_log'] = bg_log
  if not os.path.exists(bg_pid):
    os.mkdir(bg_pid)
  if not os.path.exists(bg_log):
    os.mkdir(bg_log)

  #launch all Condor wrapper
  if args['startCondor']:
    for file in args['condor_wrapper_list']:
      pid_list.append(runProcess(args, file))

  #Launch all BOINC wrapper
  if args['startBoinc']:
    for file in args['boinc_wrapper_list']:
      pid_list.append(runProcess(args, file))

  for pid in pid_list:
    print "Parent waiting for process child: %s " % pid
    result = os.waitpid(pid, 0)
    print "Done...", result
