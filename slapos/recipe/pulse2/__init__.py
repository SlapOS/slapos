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
import hashlib
import os
import pkg_resources
import sys
import zc.buildout
import ConfigParser

class Recipe(BaseSlapRecipe):
  def getTemplateFilename(self, template_name):
    return pkg_resources.resource_filename(__name__,
        'template/%s' % template_name)

  def _install(self):
    # Apache
    # TODO add in apache conf location of mmc.ini
    document_root = self.createDataDirectory('htdocs')
    self.createHtdocs(self.options['source'].strip(), document_root)
    url = self.installApache(document_root)

    # MySQL
    mysql_conf = self.installMysqlServer(self.getLocalIPv4Address(), 45678)

    # LDAP
    ldap_port = dict()

    # Pulse
    mmc_core_conf = self.installPulse2(ip=self.getLocalIPv4Address(),
        port=11000, ldap_host=ldap_conf['host'], ldap_port=ldap_conf['port'])

    ca_conf = self.installCertificateAuthority()
    key, certificate = self.requestCertificate('Pulse')

    stunnel_conf = self.installStunnel(self.getGlobalIPv6Address(),
        self.getLocalIPv4Address(), 12345, pulse_conf['inventory_port'],
        certificate, key, ca_conf['ca_crl'],
        ca_conf['certificate_authority_path'])

    self.linkBinary()
    self.setConnectionDict(dict(
      stunnel_inventory_ip = stunnel_conf['public_ip'],
      stunnel_inventory_port = stunnel_conf['public_port'],
      url=url,
      **mysql_conf
    ))
    return self.path_list

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

  def installStunnel(self, public_ip, private_ip, public_port, private_port,
      ca_certificate, key, ca_crl, ca_path):
    """Installs stunnel"""
    template_filename = self.getTemplateFilename('stunnel.conf.in')
    log = os.path.join(self.log_directory, 'stunnel.log')
    pid_file = os.path.join(self.run_directory, 'stunnel.pid')
    stunnel_conf = dict(
        public_ip=public_ip,
        private_ip=private_ip,
        public_port=public_port,
        pid_file=pid_file,
        log=log,
        cert = ca_certificate,
        key = key,
        ca_crl = ca_crl,
        ca_path = ca_path,
        private_port = private_port,
    )
    stunnel_conf_path = self.createConfigurationFile("stunnel.conf",
        self.substituteTemplate(template_filename,
          stunnel_conf))
    wrapper = zc.buildout.easy_install.scripts([('stunnel',
      'slapos.recipe.librecipe.execute', 'execute')], self.ws, sys.executable,
      self.wrapper_directory, arguments=[
        self.options['stunnel_binary'].strip(), stunnel_conf_path]
      )[0]
    self.path_list.append(wrapper)
    return stunnel_conf

  def installPulse2(self, ip, port, ldap_host, ldap_port):
    """Installs both mmc_core and pulse2"""
    config = dict(
        ldap_host=ldap_host,
        ldap_port=ldap_port,
        memcached_port=port,
        ldap_logfile_path= os.path.join(self.log_directory, 'ldap.log'),
        mmc_core_binary=self.options['mmc_core_binary']
    )

    #TODO write function that takes all templates in subdir and creates conf
    # files, keeping same dir structure.
    mmc_conf_path = self.createConfigurationFile(os.path.join("mmc",
        "agent", "config.ini"), self.substituteTemplate(
        self.getTemplateFilename(os.path.join("mmc_conf",
        "agent", "config.ini.in")), config))
    config['mmc_core_config_file'] = mysql_conf_path

    self.path_list.append(self.createRunningWrapper('mmc-core',
      self.substituteTemplate(self.getTemplateFilename('mmc-core.in'),
        config)))



    return dict(memcached_url='%s:%s' %
        (config['memcached_ip'], config['memcached_port']),
        memcached_ip=config['memcached_ip'],
        memcached_port=config['memcached_port'])

  def createHtdocs(self, source, document_root):
    source = self.options['source'].strip()
    document_root = self.createDataDirectory('htdocs')
    for p in os.listdir(document_root):
      path = os.path.join(document_root, p)
      if os.path.isdir(path):
        shutil.rmtree(path)
      else:
        os.unlink(path)
    for p in os.listdir(source):
      path = os.path.join(source, p)
      if os.path.isdir(path):
        shutil.copytree(path, os.path.join(document_root, p))
      else:
        shutil.copy2(path, os.path.join(document_root, p))

  def installApache(self, document_root, ip=None, port=None):
    if ip is None:
      ip=self.getGlobalIPv6Address()
    if port is None:
      port = '9080'
    apache_config = dict(
        pid_file=os.path.join(self.run_directory, 'httpd.pid'),
        lock_file=os.path.join(self.run_directory, 'httpd.lock'),
        ip=ip,
        port=port,
        error_log=os.path.join(self.log_directory, 'httpd-error.log'),
        access_log=os.path.join(self.log_directory, 'httpd-access.log'),
        document_root=document_root,
        php_ini_dir=self.etc_directory
    )
    config_file = self.createConfigurationFile('httpd.conf',
        self.substituteTemplate(pkg_resources.resource_filename(__name__,
          'template/apache.in'), apache_config))
    self.path_list.append(config_file)
    self.path_list.append(self.createConfigurationFile('php.ini',
        self.substituteTemplate(pkg_resources.resource_filename(__name__,
          'template/php.ini.in'), {})))
    self.path_list.extend(zc.buildout.easy_install.scripts([(
      'httpd',
        __name__ + '.apache', 'runApache')], self.ws,
          sys.executable, self.wrapper_directory, arguments=[
            dict(
              required_path_list=[],
              binary=self.options['httpd_binary'],
              config=config_file
            )
          ]))
    return 'http://[%s]:%s' % (ip, port)

  def installMysqlServer(self, ip, port, database='erp5', user='user',
      test_database='test_erp5', test_user='test_user', template_filename=None,
      parallel_test_database_amount=100, mysql_conf=None):
    if mysql_conf is None:
      mysql_conf = {}
    backup_directory = self.createBackupDirectory('mysql')
    if template_filename is None:
      template_filename = self.getTemplateFilename('my.cnf.in')
    error_log = os.path.join(self.log_directory, 'mysqld.log')
    slow_query_log = os.path.join(self.log_directory, 'mysql-slow.log')
    mysql_conf.update(
        ip=ip,
        data_directory=os.path.join(self.data_root_directory,
          'mysql'),
        tcp_port=port,
        pid_file=os.path.join(self.run_directory, 'mysqld.pid'),
        socket=os.path.join(self.run_directory, 'mysqld.sock'),
        error_log=error_log,
        slow_query_log=slow_query_log,
        mysql_database=database,
        mysql_user=user,
        mysql_password=self.generatePassword(),
        mysql_test_password=self.generatePassword(),
        mysql_test_database=test_database,
        mysql_test_user=test_user,
        mysql_parallel_test_dict=[
            ('test_%i' % x,)*2 + (self.generatePassword(),) \
                 for x in xrange(0,parallel_test_database_amount)],
    )
    self.registerLogRotation('mysql', [error_log, slow_query_log],
        '%(mysql_binary)s --no-defaults -B --user=root '
        '--socket=%(mysql_socket)s -e "FLUSH LOGS"' % dict(
          mysql_binary=self.options['mysql_binary'],
          mysql_socket=mysql_conf['socket']))
    self._createDirectory(mysql_conf['data_directory'])

    mysql_conf_path = self.createConfigurationFile("my.cnf",
        self.substituteTemplate(template_filename,
          mysql_conf))

    mysql_script_list = []
    for x_database, x_user, x_password in \
          [(mysql_conf['mysql_database'],
            mysql_conf['mysql_user'],
            mysql_conf['mysql_password']),
           (mysql_conf['mysql_test_database'],
            mysql_conf['mysql_test_user'],
            mysql_conf['mysql_test_password']),
          ] + mysql_conf['mysql_parallel_test_dict']:
      mysql_script_list.append(pkg_resources.resource_string(__name__,
                     'template/initmysql.sql.in') % {
                        'mysql_database': x_database,
                        'mysql_user': x_user,
                        'mysql_password': x_password})
    mysql_script_list.append('EXIT')
    mysql_script = '\n'.join(mysql_script_list)
    self.path_list.extend(zc.buildout.easy_install.scripts([('mysql_update',
      __name__ + '.mysql', 'updateMysql')], self.ws,
      sys.executable, self.wrapper_directory, arguments=[dict(
        mysql_script=mysql_script,
        mysql_binary=self.options['mysql_binary'].strip(),
        mysql_upgrade_binary=self.options['mysql_upgrade_binary'].strip(),
        socket=mysql_conf['socket'],
        )]))
    self.path_list.extend(zc.buildout.easy_install.scripts([('mysqld',
      __name__ + '.mysql', 'runMysql')], self.ws,
        sys.executable, self.wrapper_directory, arguments=[dict(
        mysql_install_binary=self.options['mysql_install_binary'].strip(),
        mysqld_binary=self.options['mysqld_binary'].strip(),
        data_directory=mysql_conf['data_directory'].strip(),
        mysql_binary=self.options['mysql_binary'].strip(),
        socket=mysql_conf['socket'].strip(),
        configuration_file=mysql_conf_path,
       )]))
    self.path_list.extend([mysql_conf_path])

    # backup configuration
    backup_directory = self.createBackupDirectory('mysql')
    full_backup = os.path.join(backup_directory, 'full')
    incremental_backup = os.path.join(backup_directory, 'incremental')
    self._createDirectory(full_backup)
    self._createDirectory(incremental_backup)
    innobackupex_argument_list = [self.options['perl_binary'],
        self.options['innobackupex_binary'],
        '--defaults-file=%s' % mysql_conf_path,
        '--socket=%s' %mysql_conf['socket'].strip(), '--user=root',
        '--ibbackup=%s'% self.options['xtrabackup_binary']]
    environment = dict(PATH='%s' % self.bin_directory)
    innobackupex_incremental = zc.buildout.easy_install.scripts([(
      'innobackupex_incremental','slapos.recipe.librecipe.execute', 'executee')],
      self.ws, sys.executable, self.bin_directory, arguments=[
        innobackupex_argument_list + ['--incremental'],
        environment])[0]
    self.path_list.append(innobackupex_incremental)
    innobackupex_full = zc.buildout.easy_install.scripts([('innobackupex_full',
     'slapos.recipe.librecipe.execute', 'executee')], self.ws,
      sys.executable, self.bin_directory, arguments=[
        innobackupex_argument_list,
        environment])[0]
    self.path_list.append(innobackupex_full)
    backup_controller = zc.buildout.easy_install.scripts([
      ('innobackupex_controller', __name__ + '.innobackupex', 'controller')],
      self.ws, sys.executable, self.bin_directory,
      arguments=[innobackupex_incremental, innobackupex_full, full_backup,
        incremental_backup])[0]
    self.path_list.append(backup_controller)
    mysql_backup_cron = os.path.join(self.cron_d, 'mysql_backup')
    open(mysql_backup_cron, 'w').write('0 0 * * * ' + backup_controller)
    self.path_list.append(mysql_backup_cron)
    # The return could be more explicit database, user ...
    return mysql_conf

