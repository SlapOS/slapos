# -*- coding: utf-8 -*-

import logging

from slapos.cli.config import ConfigCommand

from slapos.grid.utils import setRunning, setFinished
from slapos.grid.slapgrid import (merged_options, check_missing_parameters, check_missing_files,
                                  random_delay, create_slapgrid_object)


class SlapgridCommand(ConfigCommand):

    log = logging.getLogger(__name__)

    method_name = NotImplemented
    default_pidfile = NotImplemented

    CONSOLE_MESSAGE_FORMAT = '%(message)s'
    LOG_FILE_MESSAGE_FORMAT = '[%(asctime)s] %(levelname)-8s %(name)s %(message)s'

    def get_parser(self, prog_name):
        ap = super(SlapgridCommand, self).get_parser(prog_name)

        # XXX TODO separate parsers for instance, software and report

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
        ap.add_argument('--buildout', default=None,
                        help='Location of buildout binary.')
        ap.add_argument('--pidfile',
                        help='The location where pidfile will be created.')
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
        ap.add_argument('--maximum-periodicity', type=int, default=None,
                        help='Periodicity at which buildout should be run in instance.')
        ap.add_argument('--promise-timeout', type=int, default=3,
                        help='Promise timeout in seconds.')
        ap.add_argument('--now', action='store_true',
                        help='Launch slapgrid without delay. Default behavior.')
        ap.add_argument('--all', action='store_true',
                        help='Launch slapgrid to process all Softare Releases '
                             'and/or Computer Partitions.')
        ap.add_argument('--only-sr',
                        help='Force the update of a single software release (use url hash), '
                             'even if is already installed. This option will make all others '
                             'sofware releases be ignored.')
        ap.add_argument('--only-cp',
                        help='Update a single or a list of computer partitions '
                             '(ie.:slappartX, slappartY), '
                             'this option will make all others computer partitions be ignored.')
        return ap

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
    """Hook for entry point to process Software Releases"""

    method_name = 'processSoftwareReleaseList'
    default_pidfile = '/opt/slapos/slapgrid-sr.pid'


class InstanceCommand(SlapgridCommand):
    """Hook for entry point to process Computer Partitions"""

    method_name = 'processComputerPartitionList'
    default_pidfile = '/opt/slapos/slapgrid-cp.pid'


class ReportCommand(SlapgridCommand):
    """Hook for entry point to process Usage Reports"""

    method_name = 'agregateAndSendUsage'
    default_pidfile = '/opt/slapos/slapgrid-ur.pid'
