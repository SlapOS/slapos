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
import operator
import sys
import zc.buildout
import zc.recipe.egg
import ConfigParser
import re
import traceback

TRUE_VALUES = ['y', 'yes', '1', 'true']

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
    base_varnish_port = 26010
    slave_instance_list = self.parameter_dict.get("slave_instance_list", [])

    self.path_list = []
    self.requirements, self.ws = self.egg.working_set()

    self.killpidfromfile = zc.buildout.easy_install.scripts(
        [('killpidfromfile', 'slapos.toolbox.killpidfromfile',
          'killpidfromfile')], self.ws, sys.executable, self.bin_directory)[0]
    self.path_list.append(self.killpidfromfile)

    rewrite_rule_list = []
    rewrite_rule_cached_list = []
    rewrite_rule_https_only_list = []
    rewrite_rule_zope_list = []
    rewrite_rule_zope_path_list = []
    slave_dict = {}
    service_dict = {}

    # Sort slave instance by reference to avoid most security issues
    slave_instance_list = sorted(slave_instance_list,
                                 key=operator.itemgetter('slave_reference'))

    # dict of used domains, only used to track duplicates
    domain_dict = {}

    for slave_instance in slave_instance_list:
      # Sanitize inputs
      backend_url = slave_instance.get("url", None)
      reference = slave_instance.get("slave_reference")
      enable_cache = slave_instance.get('enable_cache', '').lower() in TRUE_VALUES
      slave_type = slave_instance.get('type', '').lower() or None

      https_only = slave_instance.get('https-only', '').lower() in TRUE_VALUES

      # Set scheme (http? https?)
      if https_only:
        scheme = 'https://'
      else:
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

      if domain_dict.get(domain):
        # This domain already has been processed, skip this new one
        continue
      else:
        domain_dict[domain] = True

      # Define the URL where the instance will be available
      # WARNING: we use default ports (443, 80) here.
      slave_dict[reference] = "%s%s/" % (scheme, domain)

      # Check if we want varnish+stunnel cache.
      if enable_cache:
        # XXX-Cedric : need to refactor to clean code? (to many variables)
#         rewrite_rule = self.configureVarnishSlave(
#             base_varnish_port, backend_url, reference, service_dict, domain)
        rewrite_rule = self.configureSquidSlave(
            base_varnish_port, backend_url, reference, service_dict, domain)
        rewrite_rule_cached_list.append("%s %s" % (domain, backend_url))
      else:
        rewrite_rule = "%s %s" % (domain, backend_url)
#       # Temporary forbid activation of cache until it is properly tested
#       rewrite_rule = "%s %s" % (domain, backend_url)

      # Finally, if successful, we add the rewrite rule to our list of rules
      # We have 4 RewriteMaps:
      #  - One for generic (non-zope) websites, accepting both HTTP and HTTPS
      #  - One for generic websites that only accept HTTPS
      #  - Two for Zope-based websites
      if rewrite_rule:
        # We check if we have a zope slave. It requires different rewrite
        # rule structure.
        # So we will have one RewriteMap for normal websites, and one
        # RewriteMap for Zope Virtual Host Monster websites.
        if slave_type in ['zope']:
          rewrite_rule_zope_list.append(rewrite_rule)
          # For Zope, we have another dict containing the path e.g '/erp5/...
          rewrite_rule_path = "%s %s" % (domain, slave_instance.get('path', ''))
          rewrite_rule_zope_path_list.append(rewrite_rule_path)
        else:
          if https_only:
            rewrite_rule_https_only_list.append(rewrite_rule)
          else:
            rewrite_rule_list.append(rewrite_rule)

    # Certificate stuff
    #valid_certificate_str = self.parameter_dict.get("domain_ssl_ca_cert")
    #valid_key_str = self.parameter_dict.get("domain_ssl_ca_key")
    #if valid_certificate_str is None and valid_key_str is None:
    #  ca_conf = self.installCertificateAuthority()
    #  key, certificate = self.requestCertificate(frontend_domain_name)
    #else:
    #  ca_conf = self.installValidCertificateAuthority(
    #      frontend_domain_name, valid_certificate_str, valid_key_str)
    #  key = ca_conf.pop("key")
    #  certificate = ca_conf.pop("certificate")
    #if service_dict != {}:
    #  if valid_certificate_str is not None and valid_key_str is not None:
    #    self.installCertificateAuthority()
    #    stunnel_key, stunnel_certificate = \
    #        self.requestCertificate(frontend_domain_name)
    #  else:
    #    stunnel_key, stunnel_certificate = key, certificate
      stunnel_key, stunnel_certificate = self.options['key_path'], self.options['cert_path']

    key, certificate = self.options['key_path'], self.options['cert_path']
    #self.installStunnel(service_dict,
    #    stunnel_certificate, stunnel_key,
    #    self.options["ca_crl"],
    #    self.options["ca_dir"])

    apache_parameter_dict = self.installFrontendApache(
        ip_list=["[%s]" % self.getGlobalIPv6Address(),
                 self.getLocalIPv4Address()],
        port=frontend_port_number,
        cached_port=base_varnish_port + 1,
        plain_http_port=frontend_plain_http_port_number,
        name=frontend_domain_name,
        rewrite_rule_list=rewrite_rule_list,
        rewrite_rule_cached_list=rewrite_rule_cached_list,
        rewrite_rule_https_only_list=rewrite_rule_https_only_list,
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

  def configureSquidSlave(self, base_squid_port, url, reference,
      service_dict, domain):
    # Squid should use stunnel to connect to the backend
    base_squid_control_port = base_squid_port
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
    service_name = "squid_%s" % reference
    squid_ip = self.getLocalIPv4Address()
    stunnel_port = base_squid_port + 1
#    self.installSquidCache(service_name,
#      ip=squid_ip,
#      port=base_squid_port,
#      backend_host=squid_ip,
#      backend_port=stunnel_port,
#      domain=domain,
#      size="1G")
    service_dict[service_name] = dict(public_ip=squid_ip,
        public_port=stunnel_port,
        private_ip=slave_host,
        private_port=slave_port)
    return "%s http://%s:%s" % \
        (domain, squid_ip, base_squid_port)

  def _getApacheConfigurationDict(self, name, ip_list, port):
    apache_conf = dict()
    apache_conf['server_name'] = name
    apache_conf['pid_file'] = self.options['pid-file']
    apache_conf['pid_cache_file'] = self.options['cache-pid-file']
    apache_conf['lock_file'] = os.path.join(self.run_directory,
        name + '.lock')
    apache_conf['document_root'] = os.path.join(self.data_root_directory,
        'htdocs')
    apache_conf['instance_home'] = os.path.join(self.work_directory)
    apache_conf['httpd_home'] = self.options['httpd_home']
    apache_conf['ip_list'] = ip_list
    apache_conf['port'] = port
    apache_conf['server_admin'] = 'admin@'
    apache_conf['error_log'] = self.options['error-log']
    apache_conf['access_log'] = self.options['access-log']
    apache_conf['error_cache_log']  = self.options['cache-error-log']
    apache_conf['access_cache_log'] = self.options['cache-access-log']
    return apache_conf

  def installFrontendApache(self, ip_list, key, certificate, name,
                            port=4443, plain_http_port=8080,
                            cached_port=26081,
                            rewrite_rule_list=None,
                            rewrite_rule_cached_list=None,
                            rewrite_rule_zope_list=None,
                            rewrite_rule_https_only_list=None,
                            rewrite_rule_zope_path_list=None,
                            access_control_string=None):
    if rewrite_rule_list is None:
      rewrite_rule_list = []
    if rewrite_rule_cached_list is None:
      rewrite_rule_cached_list = []
    if rewrite_rule_https_only_list is None:
      rewrite_rule_zope_path_list = []
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

    # Create "custom" apache configuration files if it does not exist.
    # Note : Those files won't be erased or changed by slapgrid.
    # It can be freely customized by node admin.
    custom_apache_configuration_directory = os.path.join(
        self.data_root_directory, 'apache-conf.d')
    self._createDirectory(custom_apache_configuration_directory)
    # First one is included in the end of the apache configuration file
    custom_apache_configuration_file_location = os.path.join(
        custom_apache_configuration_directory, 'apache_frontend.custom.conf')
    if not os.path.exists(custom_apache_configuration_file_location):
      open(custom_apache_configuration_file_location, 'w')
    # Second one is included in the virtualhost of apache configuration file
    custom_apache_virtual_configuration_file_location = os.path.join(
        custom_apache_configuration_directory,
        'apache_frontend.virtualhost.custom.conf')
    if not os.path.exists(custom_apache_virtual_configuration_file_location):
      open(custom_apache_virtual_configuration_file_location, 'w')

    # Create configuration file and rewritemaps
    apachemap_path = self.createConfigurationFile(
        "apache_rewritemap_generic.txt",
        "\n".join(rewrite_rule_list)
    )
    apachecachedmap_path = self.createConfigurationFile(
        "apache_rewritemap_cached.txt",
        "\n".join(rewrite_rule_cached_list)
    )
    apachemap_httpsonly_path = self.createConfigurationFile(
        "apache_rewritemap_httpsonly.txt",
        "\n".join(rewrite_rule_https_only_list)
    )
    apachemap_zope_path = self.createConfigurationFile(
        "apache_rewritemap_zope.txt",
        "\n".join(rewrite_rule_zope_list)
    )
    apachemap_zopepath_path = self.createConfigurationFile(
        "apache_rewritemap_zopepath.txt",
        "\n".join(rewrite_rule_zope_path_list)
    )

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

    apache_conf["listen_cache"] = "\n".join([
        "Listen %s:%s" % (ip, port)
        for port in (cached_port,)
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
      apachemap_path=apachemap_path,
      apachecachedmap_path=apachecachedmap_path,
      apachemap_httpsonly_path=apachemap_httpsonly_path,
      apachemapzope_path=apachemap_zope_path,
      apachemapzopepath_path=apachemap_zopepath_path,
      apache_domain=name,
      https_port=port,
      plain_http_port=plain_http_port,
      cached_port=cached_port,
      custom_apache_conf=custom_apache_configuration_file_location,
      custom_apache_virtualhost_conf=custom_apache_virtual_configuration_file_location,
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

    apache_cached_conf_string = self.substituteTemplate(
          self.getTemplateFilename('apache_cached.conf.in'), apache_conf)

    apache_cached_config_file = self.createConfigurationFile('apache_frontend_cached.conf',
        apache_cached_conf_string)

    self.path_list.extend(zc.buildout.easy_install.scripts([(
      'frontend_cached_apache', 'slapos.recipe.erp5.apache', 'runApache')], self.ws,
          sys.executable, self.service_directory, arguments=[
            dict(
              required_path_list=[key, certificate],
              binary=self.options['httpd_binary'],
              config=apache_cached_config_file)
          ]))


    return dict(site_url="https://%s:%s/" % (name, port))
