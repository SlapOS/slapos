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
  """Run condor_submit (if needed) for job deployment"""
  time.sleep(10)
  print "Check if needed to submit %s job's" % args['appname']
  if not os.path.exists(args['sig_install']):
    print "Nothing for install or update...Exited"
    return
  # '-a', "log = out.log", '-a', "error = error.log",
  launch_args = [args['submit'], '-verbose', args['submit_file']]
  process = subprocess.Popen(launch_args, stdout=subprocess.PIPE,
              stderr=subprocess.STDOUT, cwd=args['appdir'])
  result = process.communicate()[0]
  if process.returncode is None or process.returncode != 0:
    print "Failed to execute condor_submit.\nThe error was: %s" % result
  else:
    os.unlink(args['sig_install'])

def condorStart(args):
  """Start Condor if deamons is currently stopped"""
  result = os.system(args['condor_reconfig'])
  if result != 0:
    #process failled to reconfig condor that mean that condor deamons is not curently started
    os.system(args['start_bin'])
  