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
import traceback


class Recipe(BaseSlapRecipe):

  def getTemplateFilename(self, template_name):
    return pkg_resources.resource_filename(__name__,
        'template/%s' % template_name)

  def _install(self):
    # Define directory not defined in deprecated lib
    self.service_directory = os.path.join(self.etc_directory, 'service')

    # Check for mandatory arguments
    frontend_domain_name = self.parameter_dict.get("domain")
    if frontend_domain_name is None:
      raise zc.buildout.UserError('No domain name specified. Please define '
          'the "domain" instance parameter.')

    # Define optional arguments
    frontend_port_number = self.parameter_dict.get("port", 4443)
    frontend_plain_http_port_number = self.parameter_dict.get(
        "plain_http_port", 8080)
    base_varnish_port = 26009
    slave_instance_list = self.parameter_dict.get("slave_instance_list", [])

    self.path_list = []
    self.requirements, self.ws = self.egg.working_set()

    # self.cron_d is a directory, where cron jobs can be registered
    self.cron_d = self.installCrond()
    self.logrotate_d, self.logrotate_backup = self.installLogrotate()
    self.killpidfromfile = zc.buildout.easy_install.scripts(
        [('killpidfromfile', 'slapos.recipe.erp5.killpidfromfile',
          'killpidfromfile')], self.ws, sys.executable, self.bin_directory)[0]
    self.path_list.append(self.killpidfromfile)

    rewrite_rule_list = []
    rewrite_rule_zope_list = []
    rewrite_rule_zope_path_list = []
    slave_dict = {}
    service_dict = {}

    for slave_instance in slave_instance_list:
      backend_url = slave_instance.get("url", None)
      reference = slave_instance.get("slave_reference")
      # Set scheme (http? https?)
      # Future work may allow to choose between http and https (or both?)
      scheme = 'http://'

      self.logger.info('Processing slave instance: %s' % reference)

      # Check for mandatory slave fields
      if backend_url is None:
        self.logger.warn('No "url" parameter is defined for %s slave'\
            'instance. Ignoring it.' % reference)
        continue

      # Check for custom domain (like mypersonaldomain.com)
      # If no custom domain, use generated one.
      # Note: if we get an empty custom_domain parameter, we ignore it
      domain = slave_instance.get('custom_domain')
      if isinstance(domain, basestring):
        domain = domain.strip()
      if domain is None or domain.strip() == '':
        domain = "%s.%s" % (reference.replace("-", "").lower(),
            frontend_domain_name)

      # Define the URL where the instance will be available
      # WARNING: we use default ports (443, 80) here.
      slave_dict[reference] = "%s%s/" % (scheme, domain)

      # Check if we want varnish+stunnel cache.
      if slave_instance.get("enable_cache", "").upper() in ('1', 'TRUE'):
        # XXX-Cedric : need to refactor to clean code? (to many variables)
        rewrite_rule = self.configureVarnishSlave(
            base_varnish_port, backend_url, reference, service_dict, domain)
        base_varnish_port += 2
      else:
        rewrite_rule = "%s %s" % (domain, backend_url)

      # Finally, if successful, we add the rewrite rule to our list of rules
      if rewrite_rule:
        # We check if we have a zope slave. It requires different rewrite
        # rule structure.
        # So we will have one RewriteMap for normal websites, and one
        # RewriteMap for Zope Virtual Host Monster websites.
        if slave_instance.get("type", "").lower() in ['zope']:
          rewrite_rule_zope_list.append(rewrite_rule)
          # For Zope, we have another dict containing the path e.g '/erp5/...
          rewrite_rule_path = "%s %s" % (domain, slave_instance.get('path', ''))
          rewrite_rule_zope_path_list.append(rewrite_rule_path)
        else:
          rewrite_rule_list.append(rewrite_rule)

    # Certificate stuff
    valid_certificate_str = self.parameter_dict.get("domain_ssl_ca_cert")
    valid_key_str = self.parameter_dict.get("domain_ssl_ca_key")
    if valid_certificate_str is None and valid_key_str is None:
      ca_conf = self.installCertificateAuthority()
      key, certificate = self.requestCertificate(frontend_domain_name)
    else:
      ca_conf = self.installValidCertificateAuthority(
          frontend_domain_name, valid_certificate_str, valid_key_str)
      key = ca_conf.pop("key")
      certificate = ca_conf.pop("certificate")
    if service_dict != {}:
      if valid_certificate_str is not None and valid_key_str is not None:
        self.installCertificateAuthority()
        stunnel_key, stunnel_certificate = \
            self.requestCertificate(frontend_domain_name)
      else:
        stunnel_key, stunnel_certificate = key, certificate
      self.installStunnel(service_dict,
        stunnel_certificate, stunnel_key,
        ca_conf["ca_crl"],
        ca_conf["certificate_authority_path"])

    apache_parameter_dict = self.installFrontendApache(
        ip_list=["[%s]" % self.getGlobalIPv6Address(),
                 self.getLocalIPv4Address()],
        port=frontend_port_number,
        plain_http_port=frontend_plain_http_port_number,
        name=frontend_domain_name,
        rewrite_rule_list=rewrite_rule_list,
        rewrite_rule_zope_list=rewrite_rule_zope_list,
        rewrite_rule_zope_path_list=rewrite_rule_zope_path_list,
        key=key, certificate=certificate)

    # Send connection informations about each slave
    for reference, url in slave_dict.iteritems():
      self.logger.debug("Sending connection parameters of slave "
          "instance: %s" % reference)
      try:
        connection_dict = {
            # Send the public IPs (if possible) so that user knows what IP
            # to bind to its domain name
            'frontend_ipv6_address': self.getGlobalIPv6Address(),
            'frontend_ipv4_address': self.parameter_dict.get("public-ipv4",
                self.getLocalIPv4Address()),
            'site_url': url,
        }
        self.setConnectionDict(connection_dict, reference)
      except:
        self.logger.fatal("Error while sending slave %s informations: %s",
            reference, traceback.format_exc())

    # Then set it for master instance
    self.setConnectionDict(
      dict(site_url=apache_parameter_dict["site_url"],
           frontend_ipv6_address=self.getGlobalIPv6Address(),
           frontend_ipv4_address=self.getLocalIPv4Address()))

    # Promises
    promise_config = dict(
      hostname=self.getGlobalIPv6Address(),
      port=frontend_port_number,
      python_path=sys.executable,
    )
    promise_v6 = self.createPromiseWrapper(
      'apache_ipv6',
      self.substituteTemplate(
          pkg_resources.resource_filename(
              'slapos.recipe.check_port_listening',
          'template/socket_connection_attempt.py.in'),
        promise_config))
    self.path_list.append(promise_v6)

    promise_config = dict(
      hostname=self.getLocalIPv4Address(),
      port=frontend_port_number,
      python_path=sys.executable,
    )
    promise_v4 = self.createPromiseWrapper(
      'apache_ipv4',
      self.substituteTemplate(
          pkg_resources.resource_filename(
              'slapos.recipe.check_port_listening',
          'template/socket_connection_attempt.py.in'),
        promise_config))
    self.path_list.append(promise_v4)

    return self.path_list

  def configureVarnishSlave(self, base_varnish_port, url, reference,
      service_dict, domain):
    # Varnish should use stunnel to connect to the backend
    base_varnish_control_port = base_varnish_port
    base_varnish_port += 1
    # Use regex
    host_regex = "((\[\w*|[0-9]+\.)(\:|)).*(\]|\.[0-9]+)"
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
    service_name = "varnish_%s" % reference
    varnish_ip = self.getLocalIPv4Address()
    stunnel_port = base_varnish_port + 1
    self.installVarnishCache(service_name,
      ip=varnish_ip,
      port=base_varnish_port,
      control_port=base_varnish_control_port,
      backend_host=varnish_ip,
      backend_port=stunnel_port,
      size="1G")
    service_dict[service_name] = dict(public_ip=varnish_ip,
        public_port=stunnel_port,
        private_ip=slave_host.replace("[", "").replace("]", ""),
        private_port=slave_port)
    return "%s http://%s:%s" % \
        (domain, varnish_ip, base_varnish_port)

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
   wrapper = zc.buildout.easy_install.scripts([('crond',
     'slapos.recipe.librecipe.execute', 'execute')], self.ws, sys.executable,
     self.service_directory, arguments=[
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

    # XXX-Cedric: Don't use this, but use slapos.recipe.certificate_authority
    #             from the instance profile.
    self.path_list.extend(zc.buildout.easy_install.scripts([
      ('certificate_authority', __name__ + '.certificate_authority',
         'runCertificateAuthority')],
        self.ws, sys.executable, self.service_directory, arguments=[dict(
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
    apache_conf['document_root'] = os.path.join(self.data_root_directory,
        'htdocs')
    apache_conf['instance_home'] = os.path.join(self.work_directory)
    apache_conf['httpd_home'] = self.options['httpd_home']
    apache_conf['ip_list'] = ip_list
    apache_conf['port'] = port
    apache_conf['server_admin'] = 'admin@'
    apache_conf['error_log'] = os.path.join(self.log_directory,
        'frontend-apache-error.log')
    apache_conf['access_log'] = os.path.join(self.log_directory,
        'frontend-apache-access.log')
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
      varnishd_binary=self.options["varnishd_binary"],
      control_port="%s:%s" % (ip, control_port),
      storage="file,%s/storage.bin,%s" % (directory, size))

    config_file = self.createConfigurationFile("%s.conf" % name,
      self.substituteTemplate(self.getTemplateFilename('varnish.vcl.in'),
        dict(backend_host=backend_host, backend_port=backend_port)))

    varnish_argument_list = [varnish_config['varnishd_binary'].strip(),
        "-F", "-n", directory, "-P", varnish_config["pid"], "-p",
        "cc_command=exec %s " % self.options["gcc_binary"] +\
            "-fpic -shared -o %o %s",
        "-f", config_file,
        "-a", varnish_config["port"], "-T", varnish_config["control_port"],
        "-s", varnish_config["storage"]]
    environment = dict(PATH=self.options["binutils_directory"])
    wrapper = zc.buildout.easy_install.scripts([(name,
      'slapos.recipe.librecipe.execute', 'executee')], self.ws,
      sys.executable, self.service_directory, arguments=[varnish_argument_list,
      environment])[0]
    self.path_list.append(wrapper)

    return varnish_config

  def installStunnel(self, service_dict, certificate,
      key, ca_crl, ca_path):
    """Installs stunnel
      service_dict =
        { name: (public_ip, private_ip, public_port, private_port),}
    """
    template_filename = self.getTemplateFilename('stunnel.conf.in')
    template_entry_filename = self.getTemplateFilename('stunnel.conf.entry.in')

    log = os.path.join(self.log_directory, 'stunnel.log')
    pid_file = os.path.join(self.run_directory, 'stunnel.pid')
    stunnel_conf = dict(
        pid_file=pid_file,
        log=log,
        cert = certificate,
        key = key,
        ca_crl = ca_crl,
        ca_path = ca_path,
        entry_str=''
    )
    entry_list = []
    for name, parameter_dict in service_dict.iteritems():
      parameter_dict["name"] = name
      entry_str = self.substituteTemplate(template_entry_filename,
          parameter_dict)
      entry_list.append(entry_str)

    stunnel_conf["entry_str"] = "\n".join(entry_list)
    stunnel_conf_path = self.createConfigurationFile("stunnel.conf",
        self.substituteTemplate(template_filename,
          stunnel_conf))
    wrapper = zc.buildout.easy_install.scripts([('stunnel',
      'slapos.recipe.librecipe.execute', 'execute_wait')], self.ws,
      sys.executable, self.service_directory, arguments=[
        [self.options['stunnel_binary'].strip(), stunnel_conf_path],
        [certificate, key]]
      )[0]
    self.path_list.append(wrapper)
    return stunnel_conf

  def installFrontendApache(self, ip_list, key, certificate, name,
                            port=4443, plain_http_port=8080,
                            rewrite_rule_list=None,
                            rewrite_rule_zope_list=None,
                            rewrite_rule_zope_path_list=None,
                            access_control_string=None):
    if rewrite_rule_list is None:
      rewrite_rule_list = []
    if rewrite_rule_zope_list is None:
      rewrite_rule_zope_list = []
    if rewrite_rule_zope_path_list is None:
      rewrite_rule_zope_path_list = []

    # Create htdocs, populate it with default 404 document
    htdocs_location = os.path.join(self.data_root_directory, 'htdocs')
    self._createDirectory(htdocs_location)
    notfound_file_location = os.path.join(htdocs_location, 'notfound.html')
    notfound_template_file_location = self.getTemplateFilename(
        'notfound.html')
    notfound_file_content = open(notfound_template_file_location, 'r').read()
    self._writeFile(notfound_file_location, notfound_file_content)

    # Create mod_ssl cache directory
    cache_directory_location = os.path.join(self.var_directory, 'cache')
    mod_ssl_cache_location = os.path.join(cache_directory_location,
        'httpd_mod_ssl')
    self._createDirectory(cache_directory_location)
    self._createDirectory(mod_ssl_cache_location)

    # Create "custom" apache configuration file if it does not exist.
    # Note : This file won't be erased or changed when slapgrid is ran.
    # It can be freely customized by node admin.
    custom_apache_configuration_directory = os.path.join(
        self.data_root_directory, 'apache-conf.d')
    self._createDirectory(custom_apache_configuration_directory)
    custom_apache_configuration_file_location = os.path.join(
        custom_apache_configuration_directory, 'apache_frontend.custom.conf')
    f = open(custom_apache_configuration_file_location, 'a')
    f.close()

    # Create backup of custom apache configuration
    backup_path = self.createBackupDirectory('custom_apache_conf_backup')
    backup_cron = os.path.join(self.cron_d, 'custom_apache_conf_backup')
    open(backup_cron, 'w').write(
        '''0 0 * * * %(rdiff_backup)s %(source)s %(destination)s'''%dict(
          rdiff_backup=self.options['rdiff_backup_binary'],
          source=custom_apache_configuration_directory,
          destination=backup_path))
    self.path_list.append(backup_cron)

    # Create configuration file and rewritemaps
    apachemap_name = "apachemap.txt"
    apachemapzope_name = "apachemapzope.txt"
    apachemapzopepath_name = "apachemapzopepath.txt"

    self.createConfigurationFile(apachemap_name, "\n".join(rewrite_rule_list))
    self.createConfigurationFile(apachemapzope_name,
        "\n".join(rewrite_rule_zope_list))
    self.createConfigurationFile(apachemapzopepath_name,
        "\n".join(rewrite_rule_zope_path_list))

    apache_conf = self._getApacheConfigurationDict(name, ip_list, port)
    apache_conf['ssl_snippet'] = self.substituteTemplate(
        self.getTemplateFilename('apache.ssl-snippet.conf.in'),
        dict(login_certificate=certificate,
            login_key=key,
            httpd_mod_ssl_cache_directory=mod_ssl_cache_location,
        )
    )

    apache_conf["listen"] = "\n".join([
        "Listen %s:%s" % (ip, port)
        for port in (plain_http_port, port)
        for ip in ip_list
    ])

    path = self.substituteTemplate(
        self.getTemplateFilename('apache.conf.path-protected.in'),
        dict(path='/',
             access_control_string='none',
             document_root=apache_conf['document_root'],
        )
    )

    apache_conf.update(**dict(
      path_enable=path,
      apachemap_path=os.path.join(self.etc_directory, apachemap_name),
      apachemapzope_path=os.path.join(self.etc_directory, apachemapzope_name),
      apachemapzopepath_path=os.path.join(self.etc_directory, apachemapzopepath_name),
      apache_domain=name,
      https_port=port,
      plain_http_port=plain_http_port,
      custom_apache_conf=custom_apache_configuration_file_location,
    ))

    apache_conf_string = self.substituteTemplate(
          self.getTemplateFilename('apache.conf.in'), apache_conf)

    apache_config_file = self.createConfigurationFile('apache_frontend.conf',
        apache_conf_string)
    self.path_list.append(apache_config_file)

    self.path_list.extend(zc.buildout.easy_install.scripts([(
      'frontend_apache', 'slapos.recipe.erp5.apache', 'runApache')], self.ws,
          sys.executable, self.service_directory, arguments=[
            dict(
              required_path_list=[key, certificate],
              binary=self.options['httpd_binary'],
              config=apache_config_file)
          ]))

    return dict(site_url="https://%s:%s/" % (name, port))
