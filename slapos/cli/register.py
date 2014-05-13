# -*- coding: utf-8 -*-

import getpass
import os
import re
import shutil
import stat
import sys
import subprocess

import requests

from slapos.cli.command import Command, must_be_root
from slapos.util import parse_certificate_key_pair


class RegisterCommand(Command):
    """
    register a node in the SlapOS cloud
    """
    command_group = 'node'

    def get_parser(self, prog_name):
        ap = super(RegisterCommand, self).get_parser(prog_name)

        ap.add_argument('node_name',
                        help='Name of the node')

        ap.add_argument('--interface-name',
                        default='eth0',
                        help='Primary network interface. IP of Partitions '
                             'will be added to it'
                             ' (default: %(default)s)')

        ap.add_argument('--master-url',
                        default='https://slap.vifib.com',
                        help='URL of SlapOS Master REST API'
                             ' (default: %(default)s)')

        ap.add_argument('--master-url-web',
                        default='https://www.slapos.org',
                        help='URL of SlapOS Master webservice to register certificates'
                             ' (default: %(default)s)')

        ap.add_argument('--partition-number',
                        default=10,
                        type=int,
                        help='Number of partitions to create in the SlapOS Node'
                             ' (default: %(default)s)')

        ap.add_argument('--ipv4-local-network',
                        default='10.0.0.0/16',
                        help='Subnetwork used to assign local IPv4 addresses. '
                             'It should be a not used network in order to avoid conflicts'
                             ' (default: %(default)s)')

        ap.add_argument('--ipv6-interface',
                        help='Interface name to get ipv6')

        ap.add_argument('--login-auth',
                        action='store_true',
                        help='Force login and password authentication')

        ap.add_argument('--login',
                        help='Your SlapOS Master login. '
                             'Asks it interactively, then password.')

        ap.add_argument('--password',
                        help='Your SlapOS Master password. If not provided, '
                             'asks it interactively. NOTE: giving password as parameter '
                             'should be avoided for security reasons.')

        ap.add_argument('--token',
                        help="SlapOS 'computer security' authentication token")

        ap.add_argument('--create-tap', '-t',
                        action='store_true',
                        help='Will trigger creation of one virtual "tap" interface per '
                             'Partition and attach it to primary interface. Requires '
                             'primary interface to be a bridge. '
                             'Needed to host virtual machines'
                             ' (default: %(default)s)')

        ap.add_argument('--dry-run', '-n',
                        action='store_true',
                        help='Simulate the execution steps'
                             ' (default: %(default)s)')

        return ap

    @must_be_root
    def take_action(self, args):
        try:
            conf = RegisterConfig(logger=self.app.log)
            conf.setConfig(args)
            return_code = do_register(conf)
        except SystemExit as err:
            return_code = err

        sys.exit(return_code)


# XXX dry_run will happily register a new node on the slapos master. Isn't it supposed to be no-op?


def check_credentials(url, login, password):
    """Check if login and password are correct"""
    req = requests.get(url, auth=(login, password), verify=False)
    return 'Logout' in req.text


def get_certificate_key_pair(logger, master_url_web, node_name, token=None, login=None, password=None):
    """Download certificates from SlapOS Master"""

    if token:
        req = requests.post('/'.join([master_url_web, 'add-a-server/WebSection_registerNewComputer']),
                            data={'title': node_name},
                            headers={'X-Access-Token': token},
                            verify=False)
    else:
        register_server_url = '/'.join([master_url_web, ("add-a-server/WebSection_registerNewComputer?dialog_id=WebSection_viewServerInformationDialog&dialog_method=WebSection_registerNewComputer&title={}&object_path=/erp5/web_site_module/hosting/add-a-server&update_method=&cancel_url=https%3A//www.vifib.net/add-a-server/WebSection_viewServerInformationDialog&Base_callDialogMethod=&field_your_title=Essai1&dialog_category=None&form_id=view".format(node_name))])
        req = requests.get(register_server_url, auth=(login, password), verify=False)

    if not req.ok and 'Certificate still active.' in req.text:
        # raise a readable exception if the computer name is already used,
        # instead of an opaque 500 Internal Error.
        # this will not work with the new API.
        logger.error('The node name "%s" is already in use. '
                     'Please change the name, or revoke the active '
                     'certificate if you want to replace the node.', node_name)
        sys.exit(1)

    if req.status_code == 403:
        if token:
            msg = 'Please check the authentication token or require a new one.'
        else:
            msg = 'Please check username and password.'
        logger.critical('Access denied to the SlapOS Master. %s', msg)
        sys.exit(1)
    elif not req.ok and 'NotImplementedError' in req.text and not token:
        logger.critical('This SlapOS server does not support login/password '
                        'authentication. Please use the token.')
        sys.exit(1)
    else:
        req.raise_for_status()

    return parse_certificate_key_pair(req.text)


def get_computer_name(certificate):
    """Parse certificate to get computer name and return it"""
    k = certificate.find("COMP-")
    i = certificate.find("/email", k)
    return certificate[k:i]


def save_former_config(conf):
    """Save former configuration if found"""
    former = '/etc/opt/slapos'
    if not os.path.exists(os.path.join(former, 'slapos.cfg')):
        return

    saved = former + '.old'
    while os.path.exists(saved):
        conf.logger.info('Slapos configuration detected in %s', saved)
        if saved[-1] == 'd':
            saved += '.1'
        else:
            # XXX this goes from 19 to 110
            saved = saved[:-1] + str(int(saved[-1]) + 1)
    conf.logger.info('Former slapos configuration detected '
                     'in %s moving to %s', former, saved)
    shutil.move(former, saved)


def fetch_configuration_template():
    req = requests.get('http://git.erp5.org/gitweb/slapos.core.git/blob_plain/HEAD:/slapos.cfg.example')
    req.raise_for_status()
    return req.text


def slapconfig(conf):
    """Base Function to configure slapos in /etc/opt/slapos"""
    dry_run = conf.dry_run
    # Create slapos configuration directory if needed
    slap_conf_dir = os.path.normpath(conf.slapos_configuration)

    # Make sure everybody can read slapos configuration directory:
    # Add +x to directories in path
    directory = os.path.dirname(slap_conf_dir)
    while True:
        if os.path.dirname(directory) == directory:
            break
        # Do "chmod g+xro+xr"
        os.chmod(directory, os.stat(directory).st_mode | stat.S_IXGRP | stat.S_IRGRP | stat.S_IXOTH | stat.S_IROTH)
        directory = os.path.dirname(directory)

    if not os.path.exists(slap_conf_dir):
        conf.logger.info('Creating directory: %s', slap_conf_dir)
        if not dry_run:
            os.mkdir(slap_conf_dir, 0o711)

    # Hack that should be removed when we switch to re6st
    # Force start of vpn
    openvpn_needed_file = os.path.join(slap_conf_dir, 'openvpn-needed')
    if not os.path.exists(openvpn_needed_file):
        if not dry_run:
            open(openvpn_needed_file, 'w').write('')

    user_certificate_repository_path = os.path.join(slap_conf_dir, 'ssl')
    if not os.path.exists(user_certificate_repository_path):
        conf.logger.info('Creating directory: %s', user_certificate_repository_path)
        if not dry_run:
            os.mkdir(user_certificate_repository_path, 0o711)

    key_file = os.path.join(user_certificate_repository_path, 'key')
    cert_file = os.path.join(user_certificate_repository_path, 'certificate')

    for src, dst in [(conf.key, key_file), (conf.certificate, cert_file)]:
        conf.logger.info('Copying to %r, and setting minimum privileges', dst)
        if not dry_run:
            with open(dst, 'w') as destination:
                destination.write(''.join(src))
            os.chmod(dst, 0o600)
            os.chown(dst, 0, 0)

    certificate_repository_path = os.path.join(slap_conf_dir, 'ssl', 'partition_pki')
    if not os.path.exists(certificate_repository_path):
        conf.logger.info('Creating directory: %s', certificate_repository_path)
        if not dry_run:
            os.mkdir(certificate_repository_path, 0o711)

    # Put slapos configuration file
    config_path = os.path.join(slap_conf_dir, 'slapos.cfg')

    # XXX: We should actually get the template from the egg, not from git
    cfg = fetch_configuration_template()

    to_replace = [
        ('computer_id', conf.computer_id),
        ('master_url', conf.master_url),
        ('key_file', key_file),
        ('cert_file', cert_file),
        ('certificate_repository_path', certificate_repository_path),
        ('interface_name', conf.interface_name),
        ('ipv4_local_network', conf.ipv4_local_network),
        ('partition_amount', conf.partition_number),
        ('create_tap', conf.create_tap)
    ]
    if conf.ipv6_interface:
        to_replace.append(('ipv6_interface', conf.ipv6_interface))

    for key, value in to_replace:
        cfg = re.sub('\n\s*%s\s*=.*' % key, '\n%s = %s' % (key, value), cfg)

    if not dry_run:
        with open(config_path, 'w') as fout:
            fout.write(cfg.encode('utf8'))

    conf.logger.info('SlapOS configuration written to %s', config_path)


class RegisterConfig(object):
    """
    Class containing all parameters needed for configuration
    """

    def __init__(self, logger):
        self.logger = logger

    def setConfig(self, options):
        """
        Set options given by parameters.
        """
        # Set options parameters
        for option, value in options.__dict__.items():
            setattr(self, option, value)

    def COMPConfig(self, slapos_configuration, computer_id, certificate, key):
        self.slapos_configuration = slapos_configuration
        self.computer_id = computer_id
        self.certificate = certificate
        self.key = key

    def displayUserConfig(self):
        self.logger.debug('Computer Name: %s', self.node_name)
        self.logger.debug('Master URL: %s', self.master_url)
        self.logger.debug('Number of partition: %s', self.partition_number)
        self.logger.info('Using Interface %s', self.interface_name)
        self.logger.debug('Ipv4 sub network: %s', self.ipv4_local_network)
        self.logger.debug('Ipv6 Interface: %s', self.ipv6_interface)


def gen_auth(conf):
    ask = True
    if conf.login:
        if conf.password:
            yield conf.login, conf.password
            ask = False
        else:
            yield conf.login, getpass.getpass()
    while ask:
        yield raw_input('SlapOS Master Login: '), getpass.getpass()


def do_register(conf):
    """Register new computer on SlapOS Master and generate slapos.cfg"""

    if conf.login or conf.login_auth:
        for login, password in gen_auth(conf):
            if check_credentials(conf.master_url_web, login, password):
                break
            conf.logger.warning('Wrong login/password')
        else:
            return 1

        certificate, key = get_certificate_key_pair(conf.logger,
                                                    conf.master_url_web,
                                                    conf.node_name,
                                                    login=login,
                                                    password=password)
    else:
        while not conf.token:
            conf.token = raw_input('Computer security token: ').strip()

        certificate, key = get_certificate_key_pair(conf.logger,
                                                    conf.master_url_web,
                                                    conf.node_name,
                                                    token=conf.token)

    # get computer id
    COMP = get_computer_name(certificate)

    # Getting configuration parameters
    conf.COMPConfig(slapos_configuration='/etc/opt/slapos/',
                    computer_id=COMP,
                    certificate=certificate,
                    key=key)

    # Save former configuration
    if not conf.dry_run:
        save_former_config(conf)
    # Prepare Slapos Configuration
    slapconfig(conf)

    conf.logger.info('Node has successfully been configured as %s.', COMP)
    conf.logger.info('Now please invoke slapos node boot on your site.')
    return 0
