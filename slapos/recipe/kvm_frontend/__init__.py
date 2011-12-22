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
from slapos.recipe.librecipe import BaseSlapRecipe
import os
import pkg_resources
import hashlib
import sys
import zc.buildout
import zc.recipe.egg
import ConfigParser

TRUE_VALUE_LIST = ['y', 'yes', '1', 'true']
FALSE_VALUE_LIST = ['n', 'no', '0', 'false']

class Recipe(BaseSlapRecipe):

  def getTemplateFilename(self, template_name):
    return pkg_resources.resource_filename(__name__,
        'template/%s' % template_name)

  def _install(self):
    self.path_list = []
    self.requirements, self.ws = self.egg.working_set()

    # self.cron_d is a directory, where cron jobs can be registered
    self.cron_d = self.installCrond()
    self.logrotate_d, self.logrotate_backup = self.installLogrotate()
    self.killpidfromfile = zc.buildout.easy_install.scripts(
        [('killpidfromfile', 'slapos.recipe.erp5.killpidfromfile',
          'killpidfromfile')], self.ws, sys.executable, self.bin_directory)[0]

    self.path_list.append(self.killpidfromfile)

    frontend_port_number = self.parameter_dict.get("port", 4443)
    frontend_domain_name = self.parameter_dict.get("domain",
        "host.vifib.net")

    # Create http server redirecting (302) to https proxy?
    redirect_plain_http = self.parameter_dict.get("redirect_plain_http", '')
    if redirect_plain_http in TRUE_VALUE_LIST:
      redirect_plain_http = '1'

    # Get all slaves, add them to config
    slave_instance_list = self.parameter_dict.get('slave_instance_list', [])
    rewrite_rule_list = []
    slave_dict = dict()
    base_url = 'https://%s:%s/' % (frontend_domain_name, frontend_port_number)
    for slave_instance in slave_instance_list:
      current_slave_dict = dict()
      current_slave_dict['host'] = slave_instance['host']
      current_slave_dict['port'] = slave_instance['port']
      if current_slave_dict['host'] is None \
          or current_slave_dict['port'] is None:
        continue
      # Is target https or http?
      current_slave_dict['https'] = slave_instance.get('https', 'true')
      if current_slave_dict['https'] in FALSE_VALUE_LIST:
        current_slave_dict['https'] = 'false'

      reference = slave_instance.get('slave_reference')
      # XXX-Cedric : how to fetch reference?
      current_slave_dict['reference'] = reference
      slave_dict[reference] = "%s%s" % (base_url, reference.replace('-', ''))
      rewrite_rule_list.append(current_slave_dict)

    # Cert stuffs
    valid_certificate_str = self.parameter_dict.get('domain_ssl_ca_cert')
    valid_key_str = self.parameter_dict.get('domain_ssl_ca_key')
    if valid_certificate_str is None and valid_key_str is None:
      ca_conf = self.installCertificateAuthority()
      key, certificate = self.requestCertificate(frontend_domain_name)
    else:
      ca_conf = self.installValidCertificateAuthority(
          frontend_domain_name, valid_certificate_str, valid_key_str)
      key = ca_conf.pop('key')
      certificate = ca_conf.pop('certificate')

    # Install node + js script
    node_parameter_dict = self.installFrontendNode(
        ip=self.getGlobalIPv6Address(),
        port=frontend_port_number,
        plain_http=redirect_plain_http,
        name=frontend_domain_name,
        rewrite_rule_list=rewrite_rule_list,
        key=key, certificate=certificate)

    # Send connection parameters of master instance
    self.setConnectionDict(
      dict(site_url=node_parameter_dict['site_url'],
           domain_ipv6_address=self.getGlobalIPv6Address()))
    # Send connection parameters of slave instances
    for slave_reference, slave_site_url in slave_dict.iteritems():
      self.setConnectionDict(
          dict(site_url=slave_site_url,
               domainname=frontend_domain_name,
               port=frontend_port_number),
          slave_instance.get('slave_reference'))

    return self.path_list

  def installLogrotate(self):
    """Installs logortate main configuration file and registers its to cron"""
    logrotate_d = os.path.abspath(os.path.join(self.etc_directory,
      'logrotate.d'))
    self._createDirectory(logrotate_d)
    logrotate_backup = self.createBackupDirectory('logrotate')
    logrotate_conf = self.createConfigurationFile("logrotate.conf",
        "include %s" % logrotate_d)
    logrotate_cron = os.path.join(self.cron_d, 'logrotate')
    state_file = os.path.join(self.data_root_directory, 'logrotate.status')
    open(logrotate_cron, 'w').write('0 0 * * * %s -s %s %s' %
        (self.options['logrotate_binary'], state_file, logrotate_conf))
    self.path_list.extend([logrotate_d, logrotate_conf, logrotate_cron])
    return logrotate_d, logrotate_backup

  def registerLogRotation(self, name, log_file_list, postrotate_script):
    """Register new log rotation requirement"""
    open(os.path.join(self.logrotate_d, name), 'w').write(
        self.substituteTemplate(self.getTemplateFilename(
          'logrotate_entry.in'),
          dict(file_list=' '.join(['"'+q+'"' for q in log_file_list]),
            postrotate=postrotate_script, olddir=self.logrotate_backup)))

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

  def installValidCertificateAuthority(self, domain_name, certificate, key):
    ca_dir = os.path.join(self.data_root_directory, 'ca')
    ca_private = os.path.join(ca_dir, 'private')
    ca_certs = os.path.join(ca_dir, 'certs')
    ca_crl = os.path.join(ca_dir, 'crl')
    self._createDirectory(ca_dir)
    for path in (ca_private, ca_certs, ca_crl):
      self._createDirectory(path)
    key_path = os.path.join(ca_private, domain_name + ".key")
    certificate_path = os.path.join(ca_certs, domain_name + ".crt")
    self._writeFile(key_path, key)
    self._writeFile(certificate_path, certificate)
    return dict(certificate_authority_path=ca_dir,
        ca_crl=ca_crl,
        certificate=certificate_path,
        key=key_path)

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
      ('certificate_authority', 'slapos.recipe.kvm.certificate_authority',
         'runCertificateAuthority')],
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

  def _getProxyTableContent(self, rewrite_rule_list):
    proxy_table_content = '{'
    for rewrite_rule in rewrite_rule_list:
      rewrite_part = self.substituteTemplate(
         self.getTemplateFilename('proxytable-host.json.in'), rewrite_rule)
      proxy_table_content = """%s%s,""" % (proxy_table_content, rewrite_part)
    proxy_table_content = '%s%s' % (proxy_table_content,
         open(self.getTemplateFilename('proxytable-vifib-snippet.json.in')).read())
    proxy_table_content = '%s}\n' % proxy_table_content
    return proxy_table_content

  def installFrontendNode(self, ip, port, key, certificate, plain_http,
                            name, rewrite_rule_list):
    # XXX-Cedric : is name necessary?
    # Create Map
    map_name = "proxy_table.json"
    map_content = self._getProxyTableContent(rewrite_rule_list)
    map_file = self.createConfigurationFile(map_name, map_content)
    self.path_list.append(map_file)
    
    # Install script
    kvm_proxy_script_in = open(self.getTemplateFilename(
          'kvm-proxy.js'), 'r').read()
    # XXX-Cedric : this is NOT a wrapper.
    kvm_proxy_script = self.createRunningWrapper("kvm-proxy.js",
        kvm_proxy_script_in)
    self.path_list.append(kvm_proxy_script)

    # Create wrapper
    wrapper = zc.buildout.easy_install.scripts([(
        "kvm_frontend", 'slapos.recipe.librecipe.execute', 'executee_wait')], self.ws,
        sys.executable, self.wrapper_directory, arguments=[
        [self.options['node_binary'].strip(), kvm_proxy_script,
        ip, str(port), key, certificate, map_file, plain_http],
        [key, certificate],
        {'NODE_PATH': self.options['node_path']}]
      )[0]
    self.path_list.append(wrapper)

    return dict(site_url="https://%s:%s/" % (name, port))
