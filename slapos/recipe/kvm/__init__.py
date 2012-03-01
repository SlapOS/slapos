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
import sys
from slapos.recipe.librecipe import BaseSlapRecipe
import subprocess
import binascii
import random
import zc.buildout
import pkg_resources
import ConfigParser
import hashlib

class Recipe(BaseSlapRecipe):

  # To avoid magic numbers
  VNC_BASE_PORT = 5900

  def _install(self):
    """
    Set the connection dictionnary for the computer partition and create a list
    of paths to the different wrappers

    Parameters : none

    Returns    : List path_list
    """
    self.path_list = []

    self.requirements, self.ws           = self.egg.working_set()
    self.cron_d                          = self.installCrond()

    self.ca_conf                         = self.installCertificateAuthority()
    self.key_path, self.certificate_path = self.requestCertificate('noVNC')

    # Install the socket_connection_attempt script
    catcher = zc.buildout.easy_install.scripts(
      [('check_port_listening', 'slapos.recipe.kvm.socket_connection_attempt',
        'connection_attempt')],
      self.ws,
      sys.executable,
      self.bin_directory,
    )
    # Save the check_port_listening script path
    check_port_listening_script = catcher[0]
    # Get the port_listening_promise template path, and save it
    self.port_listening_promise_path = pkg_resources.resource_filename(
      __name__, 'template/port_listening_promise.in')
    self.port_listening_promise_conf = dict(
     check_port_listening_script=check_port_listening_script,
    )

    kvm_conf = self.installKvm(vnc_ip = self.getLocalIPv4Address())

    vnc_port = Recipe.VNC_BASE_PORT + kvm_conf['vnc_display']

    noVNC_conf = self.installNoVnc(source_ip   = self.getGlobalIPv6Address(),
                                   source_port = 6080,
                                   target_ip   = kvm_conf['vnc_ip'],
                                   target_port = vnc_port)

    self.linkBinary()
    self.computer_partition.setConnectionDict(dict(
        url = "https://[%s]:%s/vnc_auto.html?host=[%s]&port=%s&encrypt=1" % (
            noVNC_conf['source_ip'],
            noVNC_conf['source_port'],
            noVNC_conf['source_ip'],
            noVNC_conf['source_port']),
        password = kvm_conf['vnc_passwd']))

    return self.path_list

  def installKvm(self, vnc_ip):
    """
    Create kvm configuration dictionnary and instanciate a wrapper for kvm and
    kvm controller

    Parameters : IP the vnc server is listening on

    Returns    : Dictionnary kvm_conf
    """
    kvm_conf = dict(vnc_ip = vnc_ip)

    connection_found = False
    for tap_interface, dummy in self.parameter_dict['ip_list']:
      # Get an ip associated to a tap interface
      if tap_interface:
        connection_found = True
    if not connection_found:
      raise NotImplementedError("Do not support ip without tap interface")

    kvm_conf['tap_interface'] = tap_interface

    # Disk path
    kvm_conf['disk_path'] = os.path.join(self.data_root_directory,
        'virtual.qcow2')
    kvm_conf['socket_path'] = os.path.join(self.var_directory, 'qmp_socket')
    # XXX Weak password
    ##XXX -Vivien: add an option to generate one password for all instances
    # and/or to input it yourself
    kvm_conf['vnc_passwd'] = binascii.hexlify(os.urandom(4))

    #XXX pid_file path, database_path, path to python binary and xml path
    kvm_conf['pid_file_path'] = os.path.join(self.run_directory, 'pid_file')
    kvm_conf['database_path'] = os.path.join(self.data_root_directory,
        'slapmonitor_database')
    kvm_conf['python_path']   = sys.executable
    kvm_conf['qemu_path']     = self.options['qemu_path']
    #xml_path = os.path.join(self.var_directory, 'slapreport.xml' )

    # Create disk if needed
    if not os.path.exists(kvm_conf['disk_path']):
      retcode = subprocess.call(["%s create -f qcow2 %s %iG" % (
          self.options['qemu_img_path'], kvm_conf['disk_path'],
          int(self.options['disk_size']))], shell=True)
      if retcode != 0:
        raise OSError, "Disk creation failed!"

    # Options nbd_ip and nbd_port are provided by slapos master
    kvm_conf['nbd_ip']   = self.parameter_dict['nbd_ip']
    kvm_conf['nbd_port'] = self.parameter_dict['nbd_port']

    # First octet has to represent a locally administered address
    octet_list         = [254] + [random.randint(0x00, 0xff) for x in range(5)]
    kvm_conf['mac_address'] = ':'.join(['%02x' % x for x in octet_list])

    kvm_conf['hostname']    = "slaposkvm"
    kvm_conf['smp_count']   = self.options['smp_count']
    kvm_conf['ram_size']    = self.options['ram_size']

    kvm_conf['vnc_display'] = 1

    # Instanciate KVM
    kvm_template_location = pkg_resources.resource_filename(
                                             __name__, os.path.join(
                                             'template', 'kvm_run.in'))

    kvm_runner_path = self.createRunningWrapper("kvm",
          self.substituteTemplate(kvm_template_location,
                                  kvm_conf))

    self.path_list.append(kvm_runner_path)

    # Instanciate KVM controller
    kvm_controller_template_location = pkg_resources.resource_filename(
                                             __name__, os.path.join(
                                             'template',
                                             'kvm_controller_run.in' ))

    kvm_controller_runner_path = self.createRunningWrapper("kvm_controller",
          self.substituteTemplate(kvm_controller_template_location,
                                  kvm_conf))

    self.path_list.append(kvm_controller_runner_path)

    # Instanciate Slapmonitor
    ##slapmonitor_runner_path = self.instanciate_wrapper("slapmonitor",
    #    [database_path, pid_file_path, python_path])
    # Instanciate Slapreport
    ##slapreport_runner_path = self.instanciate_wrapper("slapreport",
    #    [database_path, python_path])

    # Add VNC promise
    self.port_listening_promise_conf.update(
      hostname=kvm_conf['vnc_ip'],
      port=Recipe.VNC_BASE_PORT + kvm_conf['vnc_display'],
    )
    self.createPromiseWrapper("vnc_promise",
        self.substituteTemplate(self.port_listening_promise_path,
                                self.port_listening_promise_conf,
                               )
                             )

    return kvm_conf

  def installNoVnc(self, source_ip, source_port, target_ip, target_port):
    """
    Create noVNC configuration dictionnary and instanciate Websockify proxy

    Parameters : IP of the proxy, port on which is situated the proxy,
                 IP of the vnc server, port on which is situated the vnc server,
                 path to python binary

    Returns    : noVNC configuration dictionnary
    """

    noVNC_conf = {}

    noVNC_conf['source_ip']   = source_ip
    noVNC_conf['source_port'] = source_port

    execute_arguments = [[
        self.options['websockify'].strip(),
        '--web',
        self.options['noVNC_location'],
        '--key=%s' % (self.key_path),
        '--cert=%s' % (self.certificate_path),
        '--ssl-only',
        '%s:%s' % (source_ip, source_port),
        '%s:%s' % (target_ip, target_port)],
        [self.certificate_path, self.key_path]]

    self.path_list.extend(zc.buildout.easy_install.scripts([('websockify',
      'slapos.recipe.librecipe.execute', 'execute_wait')], self.ws, sys.executable,
      self.wrapper_directory, arguments=execute_arguments))

    # Add noVNC promise
    self.port_listening_promise_conf.update(hostname=noVNC_conf['source_ip'],
                                            port=noVNC_conf['source_port'],
                                           )
    self.createPromiseWrapper("novnc_promise",
        self.substituteTemplate(self.port_listening_promise_path,
                                self.port_listening_promise_conf,
                               )
                             )

    return noVNC_conf

  def linkBinary(self):
    """Links binaries to instance's bin directory for easier exposal"""
    for linkline in self.options.get('link_binary_list', '').splitlines():
      if not linkline:
        continue
      target = linkline.split()
      if len(target) == 1:
        target = target[0]
        path, linkname = os.path.split(target)
      else:
        linkname = target[1]
        target = target[0]
      link = os.path.join(self.bin_directory, linkname)
      if os.path.lexists(link):
        if not os.path.islink(link):
          raise zc.buildout.UserError(
              'Target link already %r exists but it is not link' % link)
        os.unlink(link)
      os.symlink(target, link)
      self.logger.debug('Created link %r -> %r' % (link, target))
      self.path_list.append(link)

  def installCertificateAuthority(self, ca_country_code='XX',
      ca_email='xx@example.com', ca_state='State', ca_city='City',
      ca_company='Company'):
    backup_path = self.createBackupDirectory('ca')
    self.ca_dir = os.path.join(self.data_root_directory, 'ca')
    self._createDirectory(self.ca_dir)
    self.ca_request_dir = os.path.join(self.ca_dir, 'requests')
    self._createDirectory(self.ca_request_dir)
    config = dict(ca_dir=self.ca_dir, request_dir=self.ca_request_dir)
    self.ca_private = os.path.join(self.ca_dir, 'private')
    self.ca_certs = os.path.join(self.ca_dir, 'certs')
    self.ca_crl = os.path.join(self.ca_dir, 'crl')
    self.ca_newcerts = os.path.join(self.ca_dir, 'newcerts')
    self.ca_key_ext = '.key'
    self.ca_crt_ext = '.crt'
    for d in [self.ca_private, self.ca_crl, self.ca_newcerts, self.ca_certs]:
      self._createDirectory(d)
    for f in ['crlnumber', 'serial']:
      if not os.path.exists(os.path.join(self.ca_dir, f)):
        open(os.path.join(self.ca_dir, f), 'w').write('01')
    if not os.path.exists(os.path.join(self.ca_dir, 'index.txt')):
      open(os.path.join(self.ca_dir, 'index.txt'), 'w').write('')
    openssl_configuration = os.path.join(self.ca_dir, 'openssl.cnf')
    config.update(
        working_directory=self.ca_dir,
        country_code=ca_country_code,
        state=ca_state,
        city=ca_city,
        company=ca_company,
        email_address=ca_email,
    )
    self._writeFile(openssl_configuration, pkg_resources.resource_string(
      __name__, 'template/openssl.cnf.ca.in') % config)
    self.path_list.extend(zc.buildout.easy_install.scripts([
      ('certificate_authority',
        __name__ + '.certificate_authority', 'runCertificateAuthority')],
        self.ws, sys.executable, self.wrapper_directory, arguments=[dict(
          openssl_configuration=openssl_configuration,
          openssl_binary=self.options['openssl_binary'],
          certificate=os.path.join(self.ca_dir, 'cacert.pem'),
          key=os.path.join(self.ca_private, 'cakey.pem'),
          crl=os.path.join(self.ca_crl),
          request_dir=self.ca_request_dir
          )]))
    # configure backup
    backup_cron = os.path.join(self.cron_d, 'ca_rdiff_backup')
    open(backup_cron, 'w').write(
        '''0 0 * * * %(rdiff_backup)s %(source)s %(destination)s'''%dict(
          rdiff_backup=self.options['rdiff_backup_binary'],
          source=self.ca_dir,
          destination=backup_path))
    self.path_list.append(backup_cron)

    return dict(
      ca_certificate=os.path.join(config['ca_dir'], 'cacert.pem'),
      ca_crl=os.path.join(config['ca_dir'], 'crl'),
      certificate_authority_path=config['ca_dir']
    )

  def requestCertificate(self, name):
    hash = hashlib.sha512(name).hexdigest()
    key = os.path.join(self.ca_private, hash + self.ca_key_ext)
    certificate = os.path.join(self.ca_certs, hash + self.ca_crt_ext)
    parser = ConfigParser.RawConfigParser()
    parser.add_section('certificate')
    parser.set('certificate', 'name', name)
    parser.set('certificate', 'key_file', key)
    parser.set('certificate', 'certificate_file', certificate)
    parser.write(open(os.path.join(self.ca_request_dir, hash), 'w'))
    return key, certificate

  def installCrond(self):
    timestamps = self.createDataDirectory('cronstamps')
    cron_output = os.path.join(self.log_directory, 'cron-output')
    self._createDirectory(cron_output)
    catcher = zc.buildout.easy_install.scripts([('catchcron',
      __name__ + '.catdatefile', 'catdatefile')], self.ws, sys.executable,
      self.bin_directory, arguments=[cron_output])[0]
    self.path_list.append(catcher)
    cron_d = os.path.join(self.etc_directory, 'cron.d')
    crontabs = os.path.join(self.etc_directory, 'crontabs')
    self._createDirectory(cron_d)
    self._createDirectory(crontabs)
    # Use execute from erp5.
    wrapper = zc.buildout.easy_install.scripts([('crond',
      'slapos.recipe.librecipe.execute', 'execute')], self.ws, sys.executable,
      self.wrapper_directory, arguments=[
        self.options['dcrond_binary'].strip(), '-s', cron_d, '-c', crontabs,
        '-t', timestamps, '-f', '-l', '5', '-M', catcher]
      )[0]
    self.path_list.append(wrapper)
    return cron_d
