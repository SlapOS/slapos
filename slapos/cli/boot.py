# -*- coding: utf-8 -*-

import subprocess
from time import sleep
import socket
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
    print "[BOOT] [ERROR] IPv4 network unreachable..."
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
