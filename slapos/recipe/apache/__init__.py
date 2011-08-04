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
import re


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

    ca_conf = self.installCertificateAuthority()

    # This should come from parameter.
    frontend_port_number = 4443
    frontend_domain_name = self.parameter_dict.get("domain",
        "host.vifib.net")

    key, certificate = self.requestCertificate(frontend_domain_name)

    base_varnish_port = 26009
    slave_instance_list = self.parameter_dict.get("slave_instance_list", [])
    rewrite_rule_list = []
    slave_dict = {}
    stunnel_list = []
    base_url = "https://%s:%s/" % (frontend_domain_name, frontend_port_number)
    for slave_instance in slave_instance_list:
      url = slave_instance.get("url")
      reference = slave_instance.get("slave_reference")
      if url is None:
        continue
      rewrite_rule_list.append("%s %s" % (reference.replace("-", ""), url))
      slave_dict[reference] = "%s%s" % (base_url, reference.replace("-", ""))

      enable_cache = slave_instance.get("enable_cache", "")
      if enable_cache.upper() in ('1', 'TRUE'):
        # Varnish should use stunnel to connect to the backend
        base_varnish_control_port = base_varnish_port + 1
        base_varnish_port += 2
        # Use regex
        host_regex = "((\[\w*|[0-9]+\.)(\:|)).*(\]|\.[0-9])"
        slave_host = re.search(host_regex, url).group(0)
        port_regex = "\w+(\/|)$"
        matcher = re.search(port_regex, url)
        if matcher is not None:
          slave_port = matcher.group(0)
          slave_port = slave_port.replace("/", "")
        elif url.startswith("https://"):
          slave_port = 443
        else:
          slave_port = 80

        self.installVarnishCache(name="varnish",
                                 ip=self.getLocalIPv4Address(), 
                                 port=base_varnish_port,
                                 control_port=base_varnish_control_port,
                                 backend_host=slave_host,
                                 backend_port=slave_port,
                                 size="1G")

    apache_parameter_dict = self.installFrontendApache(
        ip_list=["[%s]" % self.getGlobalIPv6Address(), 
                 self.getLocalIPv4Address()],
        port=frontend_port_number, 
        name=frontend_domain_name,
        rewrite_rule_list=rewrite_rule_list,
        key=key, certificate=certificate)

    for reference, url in slave_dict.iteritems():
      self.setConnectionDict(dict(site_url=url), reference)

    self.setConnectionDict(
      dict(site_url=apache_parameter_dict["site_url"],
           domain_ipv6_address=self.getGlobalIPv6Address(), 
           domain_ipv4_address=self.getLocalIPv4Address()))
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
      ('certificate_authority', 'slapos.recipe.erp5.certificate_authority',
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

  def _getApacheConfigurationDict(self, name, ip_list, port):
    apache_conf = dict()
    apache_conf['server_name'] = name
    apache_conf['pid_file'] = os.path.join(self.run_directory,
        name + '.pid')
    apache_conf['lock_file'] = os.path.join(self.run_directory,
        name + '.lock')
    apache_conf['ip_list'] = ip_list
    apache_conf['port'] = port
    apache_conf['server_admin'] = 'admin@'
    apache_conf['error_log'] = os.path.join(self.log_directory,
        name + '-error.log')
    apache_conf['access_log'] = os.path.join(self.log_directory,
        name + '-access.log')
    self.registerLogRotation(name, [apache_conf['error_log'],
      apache_conf['access_log']], self.killpidfromfile + ' ' +
      apache_conf['pid_file'] + ' SIGUSR1')
    return apache_conf

  def installVarnishCache(self, name, ip, port, control_port, backend_host,
                                backend_port, size="1G"):
    """
      Install a varnish daemon for a certain address
    """
    directory = self.createDataDirectory(name)
    varnish_config = dict(
      directory=directory,
      pid = "%s/varnish.pid" % directory,
      port="%s:%s" % (ip, port),
      control_port="%s:%s" % (ip, control_port),
      storage="file,%s/storage.bin,%s" % (directory, size))

    config_file = self.createConfigurationFile("%s.conf" % name,
          self.substituteTemplate(self.getTemplateFilename(
                'varnish.vcl.in', dict(
                backend_host=backend_host,
                backend_port=backend_port))))

    varnish_config["configuration_file"] = config_file

    self.path_list.append(self.createRunningWrapper('varnishd',
        self.substituteTemplate(self.getTemplateFilename('varnishd.in'),
          config)))

    return varnish_config

  def installStunnel(self, service_dict, ca_certificate, key, ca_crl, ca_path):
    """Installs stunnel
	service_dict = \
	    { name: (public_ip, private_ip, public_port, private_port),}
    """
    template_filename = self.getTemplateFilename('stunnel.conf.in')
    template_entry_filename = self.getTemplateFilename('stunnel.conf.entry.in') 

    log = os.path.join(self.log_directory, 'stunnel.log')
    pid_file = os.path.join(self.run_directory, 'stunnel.pid')
    stunnel_conf = dict(
        pid_file=pid_file,
        log=log,
        cert = ca_certificate,
        key = key,
        ca_crl = ca_crl,
        ca_path = ca_path,
        entry_list=''
    )
    for service in service_dict:
      # Get template_entry_filename and generate the entry_list
      pass

    stunnel_conf_path = self.createConfigurationFile("stunnel.conf",
        self.substituteTemplate(template_filename,
          stunnel_conf))
    wrapper = zc.buildout.easy_install.scripts([('stunnel',
      'slapos.recipe.librecipe.execute', 'execute_wait')], self.ws,
      sys.executable, self.wrapper_directory, arguments=[
        [self.options['stunnel_binary'].strip(), stunnel_conf_path],
        [ca_certificate, key]]
      )[0]
    self.path_list.append(wrapper)
    return stunnel_conf

  def installFrontendApache(self, ip_list, port, key, certificate,
                            name, rewrite_rule_list, access_control_string=None):
    apachemap_name = "apachemap.txt"

    self.createConfigurationFile(apachemap_name, "\n".join(rewrite_rule_list))
    apache_conf = self._getApacheConfigurationDict(name, ip_list, port)
    apache_conf['ssl_snippet'] = self.substituteTemplate(
        self.getTemplateFilename('apache.ssl-snippet.conf.in'),
        dict(login_certificate=certificate, login_key=key))

    apache_conf["listen"] = "\n".join(["Listen %s:%s" % (ip, port) for ip in ip_list])

    path = self.substituteTemplate(
        self.getTemplateFilename('apache.conf.path-protected.in'),
        dict(path='/', access_control_string='none'))

    apache_conf.update(**dict(
      path_enable=path,
      apachemap_path=os.path.join(self.etc_directory, apachemap_name),
      apache_domain=name,
      port=port,
    ))

    apache_conf_string = self.substituteTemplate(
          self.getTemplateFilename('apache.conf.in'), apache_conf)

    apache_config_file = self.createConfigurationFile(name + '.conf',
        apache_conf_string)

    self.path_list.append(apache_config_file)
    self.path_list.extend(zc.buildout.easy_install.scripts([(
      name, 'slapos.recipe.erp5.apache', 'runApache')], self.ws,
          sys.executable, self.wrapper_directory, arguments=[
            dict(
              required_path_list=[key, certificate],
              binary=self.options['httpd_binary'],
              config=apache_config_file)
          ]))

    return dict(site_url="https://%s:%s/" % (name, port),
        slave_dict=slave_dict)
