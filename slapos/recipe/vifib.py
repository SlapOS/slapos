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
import slapos.recipe.erp5
import os
import pkg_resources
import zc.buildout
import sys

class Recipe(slapos.recipe.erp5.Recipe):

  default_bt5_list = []

  def _getZeoClusterDict(self):
    site_path = '/erp5/'
    return {
        '/': (self._requestZeoFileStorage('Zeo Server 1', 'main'),
          site_path + 'account_module'),
    }

  def installProduction(self):
    ca_conf = self.installCertificateAuthority(
        self.parameter_dict['ca_country_code'],
        self.parameter_dict['ca_email'], self.parameter_dict['ca_state'],
        self.parameter_dict['ca_city'], self.parameter_dict['ca_company'])
    memcached_conf = self.installMemcached(ip=self.getLocalIPv4Address(),
        port=11000)
    conversion_server_conf = self.installConversionServer(
        self.getLocalIPv4Address(), 23000, 23060)
    mysql_conf = self.installMysqlServer(self.getLocalIPv4Address(), 45678)
    user, password = self.installERP5()
    zodb_dir = os.path.join(self.data_root_directory, 'zodb')
    self._createDirectory(zodb_dir)
    ip = self.getLocalIPv4Address()
    mount_point_zeo_dict = self._getZeoClusterDict()
    zeo_conf = self.installZeo(ip)
    zodb_configuration_list = []
    known_tid_storage_identifier_dict = {}
    for mount_point, (storage_dict, check_path) in mount_point_zeo_dict.iteritems():
      known_tid_storage_identifier_dict[
        (((storage_dict['ip'],storage_dict['port']),), storage_dict['storage_name'])
        ] = (zeo_conf[storage_dict['storage_name']]['path'], check_path or mount_point)
      zodb_configuration_list.append(self.substituteTemplate(
        self.getTemplateFilename('zope-zeo-snippet.conf.in'), dict(
        storage_name=storage_dict['storage_name'],
        address='%s:%s' % (storage_dict['ip'], storage_dict['port']),
        mount_point=mount_point, zodb_cache_size=self.zodb_cache_size,
        zeo_client_cache_size=self.zeo_client_cache_size)))
    tidstorage_config = dict(host=self.getLocalIPv4Address(), port='6001')
    zodb_configuration_string = '\n'.join(zodb_configuration_list)
    zope_port = 12000
    # One Distribution Node
    zope_port += 1
    self.installZope(ip, zope_port, 'zope_distribution', with_timerservice=True,
        zodb_configuration_string=zodb_configuration_string,
        tidstorage_config=tidstorage_config)
    # Two Activity Nodes
    for i in (1, 2):
      zope_port += 1
      self.installZope(ip, zope_port, 'zope_activity_%s' % i,
          with_timerservice=True,
          zodb_configuration_string=zodb_configuration_string,
          tidstorage_config=tidstorage_config)
    # Four Web Page Nodes (Human access)
    login_url_list = []
    for i in (1, 2, 3, 4):
      zope_port += 1
      login_url_list.append(self.installZope(ip, zope_port,
        'zope_login_%s' % i, with_timerservice=False,
        zodb_configuration_string=zodb_configuration_string,
        tidstorage_config=tidstorage_config))
    backend_key, backend_certificate = self.requestCertificate(
        'Login Based Access')
    login_haproxy = self.installHaproxy(ip, 15001, 'login', self.site_check_path,
        login_url_list)
    apache_login = self.installBackendApache(self.getGlobalIPv6Address(), 15000,
        login_haproxy, backend_key, backend_certificate)

    # Install Frontend
    frontend_domain_name = self.parameter_dict.get("domain_name", 'vifib')
    frontend_key, frontend_certificate = \
                  self.requestCertificate(frontend_domain_name)
    apache_frontend_login = self.installFrontendZopeApache(
        self.getGlobalIPv6Address(), 4443, frontend_domain_name, '/',
        apache_login, '', frontend_key, frontend_certificate)

    # Four Web Service Nodes (Machine access)
    service_url_list = []
    for i in (1, 2, 3, 4):
      zope_port += 1
      service_url_list.append(self.installZope(ip, zope_port,
        'zope_service_%s' % i, with_timerservice=False,
        zodb_configuration_string=zodb_configuration_string,
        tidstorage_config=tidstorage_config))
    service_haproxy = self.installHaproxy(ip, 15000, 'service',
        self.site_check_path, service_url_list)

    key_auth_key, key_auth_certificate = self.requestCertificate(
        'Key Based Access')
    apache_keyauth = self.installKeyAuthorisationApache(False, 15500,
        service_haproxy, key_auth_key, key_auth_certificate, ca_conf,
        key_auth_path=self.key_auth_path)
    memcached_conf = self.installMemcached(ip=self.getLocalIPv4Address(),
        port=11000)
    kumo_conf = self.installKumo(self.getLocalIPv4Address())
    self.installTidStorage(tidstorage_config['host'], tidstorage_config['port'],
        known_tid_storage_identifier_dict, 'http://'+login_haproxy)
    self.linkBinary()

    # Connect direct to Zope to create the instance.
    self.installERP5Site(user, password, service_url_list[-1], mysql_conf,
             conversion_server_conf, memcached_conf, kumo_conf,
             self.site_id, self.default_bt5_list, ca_conf)

    self.setConnectionDict(dict(
      front_end_url=apache_frontend_login,
      site_url=apache_login,
      site_user=user,
      site_password=password,
      service_url=apache_keyauth,
      memcached_url=memcached_conf['memcached_url'],
      kumo_url=kumo_conf['kumo_address'],
      conversion_server_url='%(conversion_server_ip)s:%(conversion_server_port)s' %
        conversion_server_conf,
      # as installERP5Site is not trusted (yet) and this recipe is production
      # ready expose more information
      # XXX Use socket access to prevent unwanted connections to original MySQL
      #     server when cloning an existing ERP5 instance.
      #     TCP will be required if MySQL is in a different partition/server.
      mysql_url='%(mysql_database)s %(mysql_user)s %(mysql_password)s %(socket)s' % mysql_conf,
    ))
    return self.path_list

  def installDevelopment(self):
    ca_conf = self.installCertificateAuthority()
    memcached_conf = self.installMemcached(ip=self.getLocalIPv4Address(),
        port=11000)
    conversion_server_conf = self.installConversionServer(
        self.getLocalIPv4Address(), 23000, 23060)
    mysql_conf = self.installMysqlServer(self.getLocalIPv4Address(), 45678)
    user, password = self.installERP5()
    zodb_dir = os.path.join(self.data_root_directory, 'zodb')
    self._createDirectory(zodb_dir)
    zodb_root_path = os.path.join(zodb_dir, 'main.fs')
    ip = self.getLocalIPv4Address()
    zope_port = '18080'
    zope_access = self.installZope(ip, zope_port, 'zope_development',
        zodb_configuration_string=self.substituteTemplate(
          self.getTemplateFilename('zope-zodb-snippet.conf.in'),
          dict(zodb_root_path=zodb_root_path,
            zodb_cache_size=self.zodb_cache_size)),
          thread_amount=8, with_timerservice=True)
    service_haproxy = self.installHaproxy(ip, 15000, 'service',
        self.site_check_path, [zope_access])
    key_auth_key, key_auth_certificate = self.requestCertificate(
        'Key Based Access')
    apache_keyauth = self.installKeyAuthorisationApache(
        self.getLocalIPv4Address(), 15500, service_haproxy, key_auth_key,
        key_auth_certificate, ca_conf, key_auth_path=self.key_auth_path)
    memcached_conf = self.installMemcached(ip=self.getLocalIPv4Address(),
        port=11000)
    kumo_conf = self.installKumo(self.getLocalIPv4Address())
    self.installTestRunner(ca_conf, mysql_conf, conversion_server_conf,
        memcached_conf, kumo_conf)
    self.installTestSuiteRunner(ca_conf, mysql_conf, conversion_server_conf,
                           memcached_conf, kumo_conf)
    self.linkBinary()
    self.installERP5Site(user, password, zope_access, mysql_conf,
             conversion_server_conf, memcached_conf, kumo_conf,
             self.site_id, self.default_bt5_list, ca_conf)

    self.setConnectionDict(dict(
      development_zope='http://%s:%s/' % (ip, zope_port),
      site_user=user,
      site_password=password,
      service_url=apache_keyauth,
      memcached_url=memcached_conf['memcached_url'],
      kumo_url=kumo_conf['kumo_address'],
      conversion_server_url='%(conversion_server_ip)s:%(conversion_server_port)s' %
        conversion_server_conf,
      # as installERP5Site is not trusted (yet) and this recipe is production
      # ready expose more information
      # XXX Use socket access to prevent unwanted connections to original MySQL
      #     server when cloning an existing ERP5 instance.
      #     TCP will be required if MySQL is in a different partition/server.
      mysql_url='%(mysql_database)s %(mysql_user)s %(mysql_password)s %(socket)s' % mysql_conf,
    ))
    return self.path_list

  def _install(self):
    self.site_check_path = '/%s/getId' % self.site_id
    self.key_auth_path = '/%s/portal_slap' % self.site_id
    self.path_list = []
    self.requirements, self.ws = self.egg.working_set()
    # self.cron_d is a directory, where cron jobs can be registered
    self.zodb_cache_size = int(self.options.get('zodb_cache_size', 5000))
    self.zeo_client_cache_size = self.options.get('zeo_client_cache_size',
      '20MB')
    self.cron_d = self.installCrond()
    self.logrotate_d, self.logrotate_backup = self.installLogrotate()
    self.killpidfromfile = zc.buildout.easy_install.scripts(
        [('killpidfromfile', 'slapos.recipe.erp5.killpidfromfile',
          'killpidfromfile')], self.ws, sys.executable, self.bin_directory)[0]
    self.path_list.append(self.killpidfromfile)
    if self.parameter_dict.get("flavour", "default") == 'configurator':
      self.default_bt5_list = self.options.get("configurator_bt5_list", '').split()

    if self.parameter_dict.get('production', 'false').lower() == 'true':
      return self.installProduction()
    return self.installDevelopment()
