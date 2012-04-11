#!%(python_location)s

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
from slapos import slap
import signal
from subprocess import Popen
import sys
import time

def runAccords(accords_conf):
  """Launch ACCORDS, parse manifest, broker manifest, send connection
     informations to SlapOS Master. Destroy instance and stops ACCORDS at
     SIGTERM."""
  computer_id = accords_conf['computer_id']
  computer_partition_id = accords_conf['computer_partition_id']
  server_url = accords_conf['server_url']
  software_release_url = accords_conf['software_release_url']
  key_file = accords_conf['key_file']
  cert_file = accords_conf['cert_file']
  accords_lib_directory = accords_conf['accords_lib_directory']
  poc_location = accords_conf['poc_location']
  manifest_name = accords_conf['manifest_name']

  environment = dict(
     LD_LIBRARY_PATH=accords_lib_directory,
     PATH= accords_conf['path'],
  )

  # Set handler to stop ACCORDS when end of world comes
  def sigtermHandler(signum, frame):
    Popen(['./co-command', 'stop', '/service/*'],
        cwd=poc_location, env=environment).communicate()
    Popen(['./co-stop'],
        cwd=poc_location, env=environment).communicate()
    sys.exit(0)

  signal.signal(signal.SIGTERM, sigtermHandler)

  # Launch ACCORDS, parse & broke manifest to deploy instance
  Popen(['./co-start'],cwd=poc_location, env=environment).communicate()
  print 'Parsing manifest...'
  Popen(['./co-parser', manifest_name],
      cwd=poc_location, env=environment).communicate()
  print 'Brokering manifest...'
  Popen(['./co-broker', manifest_name],
      cwd=poc_location, env=environment).communicate()
  print 'Done.'

  # Parse answer
  # XXX
  connection_dict = dict(connection='hardcoded')

  # Send information about published service to SlapOS Master
  slap_connection = slap.slap()
  slap_connection.initializeConnection(server_url, key_file, cert_file)
  computer_partition = slap_connection.registerComputerPartition(computer_id,
      computer_partition_id)
  computer_partition.setConnectionDict(connection_dict)

  # Go to sleep, wait kill
  while(True):
    time.sleep(60)
