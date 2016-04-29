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

import os
import pkg_resources
import re
import subprocess
import sys

from slapos.cli.command import must_be_root
from slapos.format import FormatConfig
from slapos.cli.config import ConfigCommand
from slapos.grid.slapgrid import create_slapgrid_object
from slapos.grid.utils import updateFile, createPrivateDirectory
from slapos.grid.svcbackend import launchSupervisord

DEFAULT_COMPUTER_ID = 'local_computer'


class ConfigureLocalCommand(ConfigCommand):
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
                        default='8080',
                        help='Listening port of the "slapproxy" daemon'
                             ' (default: %(default)s)')

        ap.add_argument('--slapos-instance-root',
                        default='/srv/slapgrid',
                        help='Target location of the SlapOS configuration'
                             ' directory (default: %(default)s)')

        ap.add_argument('--slapos-software-root',
                        default='/opt/slapgrid',
                        help='Target location of the SlapOS configuration'
                             ' directory (default: %(default)s)')

        ap.add_argument('--slapos-buildout-directory',
                        default='/opt/slapos',
                        help='Target location of the SlapOS configuration'
                             ' directory (default: %(default)s)')

        ap.add_argument('--slapos-configuration-directory',
                        default='/etc/opt/slapos',
                        help='Target location of the SlapOS configuration'
                             ' directory (default: %(default)s)')

        return ap

    @must_be_root
    def take_action(self, args):
        try:
            return_code = do_configure(args, self.fetch_config, self.app.log)
        except SystemExit as err:
            return_code = err
        sys.exit(return_code)

def _createConfigurationDirectory(target_directory):
    target_directory = os.path.normpath(target_directory)
    if not os.path.exists(target_directory):
      os.makedirs(target_directory)

def _replaceParameterValue(original_content, to_replace):
    """
    Replace in a .ini-like file the value of all parameters specified in
    to_replace by their value.
    """
    for key, value in to_replace:
        original_content = re.sub('%s\s+=.*' % key, '%s = %s' % (key, value),
          original_content)
    return original_content

def _generateSlaposNodeConfigurationFile(slapos_node_config_path, args):
    template_arg_list = (__name__, '../../slapos.cfg.example')
    with pkg_resources.resource_stream(*template_arg_list) as fout:
      slapos_node_configuration_template = fout.read()
    master_url = 'http://%s:%s' % (args.daemon_listen_ip, args.daemon_listen_port)
    slapos_home = args.slapos_buildout_directory
    to_replace = [
        ('computer_id', DEFAULT_COMPUTER_ID),
        ('master_url', master_url),
        ('interface_name', args.interface_name),
        ('ipv4_local_network', args.ipv4_local_network),
        ('partition_amount', args.partition_number),
        ('instance_root', args.slapos_instance_root),
        ('software_root', args.slapos_software_root),
        ('computer_xml', '%s/slapos.xml' % slapos_home),
        ('log_file', '%s/log/slapos-node-format.log' % slapos_home),
        ('use_unique_local_address_block', 'false')
    ]

    slapos_node_configuration_content = _replaceParameterValue(
        slapos_node_configuration_template, to_replace)
    slapos_node_configuration_content = re.sub(
        '(key_file|cert_file|certificate_repository_path).*=.*\n',
        '', slapos_node_configuration_content)
    with open(slapos_node_config_path, 'w') as fout:
        fout.write(slapos_node_configuration_content.encode('utf8'))

def _generateSlaposProxyConfigurationFile(conf):
    template_arg_list = (__name__, '../../slapos-proxy.cfg.example')
    with pkg_resources.resource_stream(*template_arg_list) as fout:
      slapos_proxy_configuration_template = fout.read()
    slapos_proxy_configuration_path = os.path.join(
      conf.slapos_configuration_directory, 'slapos-proxy.cfg')
    listening_ip, listening_port = \
      conf.daemon_listen_ip, conf.daemon_listen_port
    to_replace = [
        ('host', listening_ip),
        ('port', listening_port),
        ('master_url', 'http://%s:%s/' % (listening_ip, listening_port)),
        ('computer_id', DEFAULT_COMPUTER_ID),
        ('instance_root', conf.instance_root),
        ('software_root', conf.software_root)
    ]

    slapos_proxy_configuration_content = _replaceParameterValue(
        slapos_proxy_configuration_template, to_replace)

    with open(slapos_proxy_configuration_path, 'w') as fout:
        fout.write(slapos_proxy_configuration_content.encode('utf8'))

    return slapos_proxy_configuration_path

def _addProxyToSupervisor(conf):
    """
    Create a supervisord configuration file containing informations to run
    slapproxy as daemon
    """
    program_partition_template = """\
[program:slapproxy]
directory=%(slapos_buildout_directory)s
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
""" % {'log_file': '%s/log/slapos-proxy.log' % conf.slapos_buildout_directory,
       'slapos_buildout_directory': conf.slapos_buildout_directory,
       'program_command': '%s/bin/slapos proxy start --cfg %s' % \
          (conf.slapos_buildout_directory, conf.proxy_configuration_file)}

    supervisord_conf_folder_path = os.path.join(conf.instance_root,
        'etc', 'supervisord.conf.d')
    _createConfigurationDirectory(supervisord_conf_folder_path)
    updateFile(
        os.path.join(supervisord_conf_folder_path, 'slapproxy.conf'),
        program_partition_template)

def _runFormat(slapos_directory):
    """
    Launch slapos node format.
    """
    subprocess.Popen(
      ["%s/bin/slapos" % slapos_directory,
        "node", "format", "--now"]).communicate()


def do_configure(args, fetch_config_func, logger):
    """
    Generate configuration files,
    Create the instance path by running slapformat (but will crash),
    Add proxy to supervisor,
    Run supervisor, which will run the proxy,
    Run format, which will finish correctly.
    """
    slapos_node_config_path = os.path.join(
        args.slapos_configuration_directory, 'slapos.cfg')
    if os.path.exists(slapos_node_config_path):
        logger.error('A SlapOS configuration directory already exist at'
                     ' %s. Aborting.' % slapos_node_config_path)
        raise SystemExit(1)
    if not getattr(args, 'cfg', None):
        args.cfg = slapos_node_config_path
    _createConfigurationDirectory(args.slapos_configuration_directory)
    _generateSlaposNodeConfigurationFile(slapos_node_config_path, args)
    configp = fetch_config_func(args)
    conf = FormatConfig(logger=logger)
    conf.mergeConfig(args, configp)
    slapgrid = create_slapgrid_object(conf.__dict__, logger)
    createPrivateDirectory(os.path.join(conf.slapos_buildout_directory, 'log'))
    _runFormat(conf.slapos_buildout_directory)
    slapgrid.checkEnvironmentAndCreateStructure()
    proxy_configuration_file = _generateSlaposProxyConfigurationFile(conf)
    conf.proxy_configuration_file = proxy_configuration_file
    _addProxyToSupervisor(conf)
    home_folder_path = os.environ['HOME']
    createPrivateDirectory("%s/.slapos" % home_folder_path)
    slapos_client_cfg_path = '%s/.slapos/slapos-client.cfg' % home_folder_path
    if not os.path.exists(slapos_client_cfg_path):
        os.symlink(slapos_node_config_path, slapos_client_cfg_path)
    launchSupervisord(instance_root=conf.instance_root, logger=logger)
    _runFormat(conf.slapos_buildout_directory)
    return 0
