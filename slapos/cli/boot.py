# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010-2014 Vifib SARL and Contributors.
# All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import subprocess
from time import sleep
import glob
import os
from slapos.cli.command import must_be_root
from slapos.cli.entry import SlapOSApp
from slapos.cli.config import ConfigCommand

def _removeTimestamp(instancehome):
    """
      Remove .timestamp from all partitions
    """
    timestamp_glob_path = "%s/slappart*/.timestamp" % instancehome
    for timestamp_path in glob.glob(timestamp_glob_path):
       print "Removing %s" % timestamp_path
       os.remove(timestamp_path)

def _runBang(app):
    """
    Launch slapos node format.
    """
    print "[BOOT] Invoking slapos node bang..."
    result = app.run(['node', 'bang', '-m', 'Reboot'])
    if result == 1:
      return 0
    return 1

def _runFormat(app):
    """
    Launch slapos node format.
    """
    print "[BOOT] Invoking slapos node format..."
    result = app.run(['node', 'format', '--now', '--verbose'])
    if result == 1:
      return 0
    return 1

def _ping():
    """ 
    Ping a hostname
    """
    print "[BOOT] Invoking ping to ipv4 network..."
    p = subprocess.Popen(
      ["ping", "-c", "2", "www.google.com"],
       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if p.returncode == 0:
      print "[BOOT] IPv4 network reachable..."
      return 1
    print "[BOOT] [ERROR] IPv4 network unreachable..."
    return 0

def _ping6():
    """ 
    Ping an ipv6 address
    """
    print "[BOOT] Invoking ping to ipv6 network..."
    p = subprocess.Popen(
        ["ping6", "-c", "2", "ipv6.google.com"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if p.returncode == 0:
        print "[BOOT] IPv6 network reachable..."
        return 1
    print "[BOOT] [ERROR] IPv6 network unreachable..."
    return 0

class BootCommand(ConfigCommand):
    """
    Test network and invoke simple format and bang (Use on Linux startup)
    """
    command_group = 'node'

    def get_parser(self, prog_name):
        ap = super(BootCommand, self).get_parser(prog_name)
        ap.add_argument('-m', '--message',
                        default="Reboot",
                        help='Message for bang')
        return ap

    @must_be_root
    def take_action(self, args):
        configp = self.fetch_config(args)
        # Make sure ipv4 is working
        instance_root = configp.get('slapos','instance_root')
        is_ready = _ping()
        while is_ready == 0:
           sleep(5)
           is_ready = _ping()

        # Make sure ipv6 is working
        is_ready = _ping6()
        while is_ready == 0:
            sleep(5)
            is_ready = _ping6()

        app = SlapOSApp() 
        # Make sure slapos node format returns ok
        is_ready = _runFormat(app)
        while is_ready == 0:
            print "[BOOT] [ERROR] Fail to format, try again in 15 seconds..."
            sleep(15)
            is_ready = _runFormat(app)
       
        # Make sure slapos node bang returns ok
        is_ready = _runBang(app)
        while is_ready == 0:
            print "[BOOT] [ERROR] Fail to bang, try again in 15 seconds..."
            sleep(15)
            is_ready = _runBang(app)

        _removeTimestamp(instance_root)
