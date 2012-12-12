# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Vifib SARL and Contributors.
# All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
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

import argparse
import os.path
import slapos.slap.slap
import sys

def getWatchdogID():
  return "-on-watch"

def parseArgumentTuple():
  """Parses arguments either from command line, from method parameters or from
     config file. Then returns a new instance of slapgrid.Slapgrid with those
     parameters. Also returns the options dict and unused variable list, and
     configures logger.
  """
  parser = argparse.ArgumentParser()
  parser.add_argument("--master-url",
                      help="The master server URL. Mandatory.",
                      required=True)
  parser.add_argument("--computer-id",
                      help="The computer id defined in the server.",
                      required=True)
  parser.add_argument("--certificate-repository-path",
                      help="Path to partition certificates.",
                      default=None)
  option = parser.parse_args()

  # Build option_dict
  option_dict = {}

  for argument_key, argument_value in vars(option).iteritems():
    option_dict.update({argument_key: argument_value})

  return option_dict


class Watchdog():

  process_state_events = ['PROCESS_STATE_EXITED', 'PROCESS_STATE_FATAL']

  def __init__(self, option_dict):
    for option, value in option_dict.items():
      setattr(self, option, value)
    self.stdin = sys.stdin
    self.stdout = sys.stdout
    self.stderr = sys.stderr
    self.slap = slapos.slap.slap()

  def initialize_connection(self, partition_id):
    cert_file = None
    key_file = None
    if self.certificate_repository_path is not None:
      cert_file = os.path.join(self.certificate_repository_path,
                              "%s.crt" % partition_id)
      key_file = os.path.join(self.certificate_repository_path,
                             "%s.key" % partition_id)
    self.slap.initializeConnection(
      slapgrid_uri=self.master_url, key_file=key_file, cert_file=cert_file)

  def write_stdout(self, s):
    self.stdout.write(s)
    self.stdout.flush()

  def write_stderr(self, s):
    self.stderr.write(s)
    self.stderr.flush()

  def run(self):
    while 1:
      self.write_stdout('READY\n')
      line = self.stdin.readline()  # read header line from stdin
      headers = dict([x.split(':') for x in line.split()])
      data = sys.stdin.read(int(headers['len'])) # read the event payload
      self.handle_event(headers, data)
      self.write_stdout('RESULT 2\nOK') # transition from READY to ACKNOWLEDGED

  def handle_event(self, headers, payload):
    if headers['eventname'] in self.process_state_events:
      payload_dict = dict([x.split(':') for x in payload.split()])
      if getWatchdogID() in payload_dict['processname']:
        self.handle_process_state_change_event(headers, payload_dict)

  def handle_process_state_change_event(self, headers, payload_dict):
    partition_id = payload_dict['groupname']
    self.initialize_connection(partition_id)
    partition = slapos.slap.ComputerPartition(
      computer_id=self.computer_id,
      connection_helper=self.slap._connection_helper,
      partition_id=partition_id)
    partition.bang("%s process in partition %s encountered a problem"
                   % (payload_dict['processname'], partition_id))


def main():
  watchdog = Watchdog(parseArgumentTuple())
  watchdog.run()

if __name__ == '__main__':
  main()
