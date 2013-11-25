# -*- coding: utf-8 -*-

##############################################################################
#
# Copyright (c) 2013 Vifib SARL and Contributors.
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

import logging
import os
import pkg_resources
import re
import subprocess
import sys

from slapos.cli.command import Command, must_be_root
from slapos.grid.utils import updateFile
from slapos.grid.svcbackend import launchSupervisord

DEFAULT_COMPUTER_ID = 'local_computer'


class ConfigureLocalCommand(Command):
    """
    Configure a slapos node, from scratch to ready-ro-use, using slapproxy.
    """

    def get_parser(self, prog_name):
        ap = super(self.__class__, self).get_parser(prog_name)

        ap.add_argument('--interface-name',
                        default='lo',
                        help='Primary network interface. IP of Partitions '
                             'will be added to it'
                             ' (default: %(default)s)')

        ap.add_argument('--partition-number',
                        default=20,
                        type=int,
                        help='Number of partitions to create in the SlapOS Node'
                             ' (default: %(default)s)')

        ap.add_argument('--ipv4-local-network',
                        default='10.0.0.0/16',
                        help='Subnetwork used to assign local IPv4 addresses. '
                             'It should be a not used network in order to'
                             ' avoid conflicts (default: %(default)s)')

        ap.add_argument('--daemon-listen-ip',
                        default='127.0.0.1',
                        help='Listening IP of the "slapproxy" daemon'
                             ' (default: %(default)s)')

        ap.add_argument('--daemon-listen-port',
                        default='127.0.0.1',
                        help='Listening port of the "slapproxy" daemon'
                             ' (default: %(default)s)')

        ap.add_argument('--slapos-configuration-directory',
                        default='/etc/opt/slapos',
                        help='Target location of the SlapOS configuration'
                             ' directory (default: %(default)s)')

        return ap

    @must_be_root
    def take_action(self, args):
        try:
            return_code = do_configure(args, logger)
        except SystemExit as err:
            return_code = err

        sys.exit(return_code)


def _createDirectoryIfNotExist(target_directory, logger):
    target_directory = os.path.normpath(target_directory)
    # XXX: hardcoded
    if os.path.exists(os.path.join(target_directory, 'slapos.cfg')):
        logger.error('A SlapOS configuration directory already exist at'
                     ' %s. Aborting.' % target_directory)
        raise SystemExit(1)
    if not os.path.exists(target_directory):
      os.mkdir(target_directory, 0o711)
    return target_directory


def _replaceParameterValue(original_content, to_replace):
    """
    Replace in a .ini-like file the value of all parameters specified in
    to_replace by their value.
    """
    # XXX: Can be cleaned up by being replaced by a simple dict
    new_content = ''
    for key, value in to_replace:
        # Replace all values of the given parameters to the specified values
        new_content = re.sub(
            '%s\s+=.*' % key, '%s = %s' % (key, value),
            original_content
        )
    return new_content

def _generateSlaposNodeConfigurationFile(target_directory,
                                         listening_ip, listening_port,
                                         interface_name,
                                         ipv4_local_network,
                                         partition_number):
    slapos_node_configuration_template = pkg_resources.resource_stream(
        __name__, 'template/slapos.cfg.in').read()
    slapos_node_configuration_file_location = os.path.join(
        target_directory, 'slapos.cfg')
    to_replace = [
        ('computer_id', DEFAULT_COMPUTER_ID),
        ('master_url', 'http://%s:%s' % (listening_ip, listening_port)),
        ('interface_name', interface_name),
        ('ipv4_local_network', ipv4_local_network),
        ('partition_amount', partition_number),
        ('use_unique_local_address', 'true')
    ]

    slapos_node_configuration_content = _replaceParameterValue(
        slapos_node_configuration_template, to_replace)

    with open(slapos_node_configuration_file_location, 'w') as fout:
        fout.write(slapos_node_configuration_content.encode('utf8'))


def _generateSlaposProxyConfigurationFile(target_directory,
                                          listening_ip, listening_port
                                          ):
    slapos_proxy_configuration_template = pkg_resources.resource_stream(
        __name__, 'template/slapos-proxy.cfg.in').read()
    slapos_proxy_configuration_file_location = os.path.join(
        target_directory, 'slapos-proxy.cfg')
    to_replace = [
        ('host', listening_ip),
        ('port', listening_port),
    ]

    slapos_proxy_configuration_content = _replaceParameterValue(
        slapos_proxy_configuration_template, to_replace)

    with open(slapos_proxy_configuration_file_location, 'w') as fout:
        fout.write(slapos_proxy_configuration_content.encode('utf8'))

    return slapos_proxy_configuration_file_location

def _addProxyToSupervisor(proxy_configuration_file):
    """
    Create a supervisord configuration file containing informations to run
    slapproxy as daemon
    """
    # In the beginning God created SlapOS.
    # And SlapOS was without form, and void; and darkness was upon the face of the deep.
    # And God said, Let there be supervisord manager.
    # But God was drunk. The result can be found by the Brave in slapgrid, but it may turn the Brave blind forever.
    # So, for the sake of God, I'm not using that helper.

    # XXX every path here is hardcoded, assuming default values
    program_partition_template = """\
[program:slapproxy]
directory=/opt/slapos
command=%(program_command)s
process_name=slapproxy
autostart=true
autorestart=true
startsecs=0
startretries=0
exitcodes=0
stopsignal=TERM
stopwaitsecs=60
user=0
group=0
serverurl=AUTO
redirect_stderr=true
stdout_logfile=%(log_file)s
stdout_logfile_maxbytes=100KB
stdout_logfile_backups=1
stderr_logfile=%(log_file)s
stderr_logfile_maxbytes=100KB
stderr_logfile_backups=1
""" % {'log_file': '/opt/slapos/log/slapos-proxy.log',
       'program_command': '/opt/slapos/bin/slapproxy %s' % proxy_configuration_file}

    updateFile(
        '/srv/slapgrid/etc/supervisord.conf.d/slapproxy.conf',
        program_partition_template
    )

def _runFormat():
    """
    Launch slapos node format.
    """
    # XXX: hardcoded
    command = '/opt/slapos/bin/slapos node format --now -v'.split()
    subprocess.Popen(command).communicate()


def do_configure(conf, logger):
    """
    Generate configuration files,
    Create the instance path by running slapformat (but will crash),
    Add proxy to supervisor,
    Run supervisor, which will run the proxy,
    Run format, which will finish correctly.
    """
    slapos_configuration_directory = _createDirectoryIfNotExist(
        conf.slapos_configuration_directory, logger)

    _generateSlaposNodeConfigurationFile(
        slapos_configuration_directory,
        conf.daemon_listen_ip,
        conf.daemon_listen_port,
        conf.interface_name,
        conf.ipv4_local_network,
        conf.partition_number
    )
    proxy_configuration_file_location = _generateSlaposProxyConfigurationFile(
        slapos_configuration_directory,
        conf.daemon_listen_ip,
        conf.daemon_listen_port
    )
    _runFormat()
    _addProxyToSupervisor(proxy_configuration_file_location)
    # XXX hardcoded
    launchSupervisord(
        '/srv/slapgrid/supervisord.socket',
        '/srv/slapgrid/etc/supervisord.conf',
        logger=logger)
    _runFormat()
    return 0
