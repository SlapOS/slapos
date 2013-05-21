# -*- coding: utf-8 -*-

import logging

from slapos.cli.command import must_be_root
from slapos.cli.config import ConfigCommand

from slapos.grid.utils import setRunning, setFinished
from slapos.grid.slapgrid import (merged_options, check_missing_parameters, check_missing_files,
                                  random_delay, create_slapgrid_object)


class SlapgridCommand(ConfigCommand):

    log = None

    method_name = NotImplemented
    default_pidfile = NotImplemented

    def get_parser(self, prog_name):
        ap = super(SlapgridCommand, self).get_parser(prog_name)

        # TODO move more options to the instance, software and report subclasses

        ap.add_argument('--instance-root',
                        help='The instance root directory location.')
        ap.add_argument('--software-root',
                        help='The software_root directory location.')
        ap.add_argument('--master-url',
                        help='The master server URL. Mandatory.')
        ap.add_argument('--computer-id',
                        help='The computer id defined in the server.')
        ap.add_argument('--supervisord-socket',
                        help='The socket supervisor will use.')
        ap.add_argument('--supervisord-configuration-path',
                        help='The location where supervisord configuration will be stored.')
        ap.add_argument('--buildout',
                        help='Location of buildout binary.')
        ap.add_argument('--pidfile',
                        help='The location where pidfile will be created. '
                             'Can be provided by configuration file, or defaults '
                             'to %s' % self.default_pidfile)
        ap.add_argument('--key_file',
                        help='SSL Authorisation key file.')
        ap.add_argument('--cert_file',
                        help='SSL Authorisation certificate file.')
        ap.add_argument('--signature_private_key_file',
                        help='Signature private key file.')
        ap.add_argument('--master_ca_file',
                        help='Root certificate of SlapOS master key.')
        ap.add_argument('--certificate_repository_path',
                        help='Path to directory where downloaded certificates would be stored.')
        ap.add_argument('--maximum-periodicity',
                        type=int,
                        help='Periodicity at which buildout should be run in instance.')
        ap.add_argument('--promise-timeout',
                        default=3,
                        type=int,
                        help='Promise timeout in seconds'
                             ' (default: %(default)s)')
        ap.add_argument('--now',
                        action='store_true',
                        help='Launch slapgrid without delay. Default behavior.')
        return ap

    @must_be_root
    def take_action(self, args):
        configp = self.fetch_config(args)
        options = merged_options(args, configp)

        check_missing_parameters(options)
        check_missing_files(options)

        random_delay(options, logger=self.log)

        slapgrid_object = create_slapgrid_object(options, logger=self.log)

        pidfile = options.get('pidfile') or self.default_pidfile

        if pidfile:
            setRunning(logger=self.log, pidfile=pidfile)
        try:
            return getattr(slapgrid_object, self.method_name)()
        finally:
            if pidfile:
                setFinished(pidfile)


class SoftwareCommand(SlapgridCommand):
    """run software installation/deletion"""

    log = logging.getLogger('software')

    method_name = 'processSoftwareReleaseList'
    default_pidfile = '/opt/slapos/slapgrid-sr.pid'

    def get_parser(self, prog_name):
        ap = super(SoftwareCommand, self).get_parser(prog_name)

        only = ap.add_mutually_exclusive_group()
        only.add_argument('--all', action='store_true',
                          help='Process all Software Releases, even if already installed.')
        only.add_argument('--only-sr', '--only',
                          help='Force the update of a single software release (can be full URL or MD5 hash), '
                               'even if is already installed. This option will make all other '
                               'sofware releases be ignored.')
        return ap


class InstanceCommand(SlapgridCommand):
    """run instance deployment"""

    log = logging.getLogger('instance')

    method_name = 'processComputerPartitionList'
    default_pidfile = '/opt/slapos/slapgrid-cp.pid'

    def get_parser(self, prog_name):
        ap = super(InstanceCommand, self).get_parser(prog_name)

        only = ap.add_mutually_exclusive_group()
        only.add_argument('--all', action='store_true',
                          help='Process all Computer Partitions.')
        only.add_argument('--only-cp', '--only',
                          help='Update a single or a list of computer partitions '
                               '(ie.:slappartX, slappartY), '
                               'this option will make all other computer partitions be ignored.')
        return ap


class ReportCommand(SlapgridCommand):
    """run instance reports and garbage collection"""

    log = logging.getLogger('report')

    method_name = 'agregateAndSendUsage'
    default_pidfile = '/opt/slapos/slapgrid-ur.pid'
