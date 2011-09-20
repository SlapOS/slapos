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
import subprocess
import pkg_resources
import zc.buildout
import zc.recipe.egg
import sys

class Recipe(BaseSlapRecipe):
  def getTemplateFilename(self, template_name):
    return pkg_resources.resource_filename(__name__,
        'template/%s' % template_name)

  def _install(self):
    self.path_list = []
    self.requirements, self.ws = self.egg.working_set()
    document_root = self.createDataDirectory('www')
    self.apache_config = self.installApache(document_root)
    self.setConnectionDict(
      dict(url='https://[%s]:%s/' % (self.apache_config['ip'],
                                     self.apache_config['port']),
           user=self.apache_config['user'],
           password=self.apache_config['password']),
    )
    return self.path_list

  def installApache(self, document_root, ip=None, port=None):
    if ip is None:
      ip=self.getGlobalIPv6Address()
    if port is None:
      port = '9080'

    htpasswd_config = self.createHtpasswd()
    ssl_config = self.createCertificate(size=2048)

    apache_config = dict(
      pid_file=os.path.join(self.run_directory, 'httpd.pid'),
      lock_file=os.path.join(self.run_directory, 'httpd.lock'),
      davlock_db=os.path.join(self.run_directory, 'davdb.lock'),
      ip=ip,
      port=port,
      error_log=os.path.join(self.log_directory, 'httpd-error.log'),
      access_log=os.path.join(self.log_directory, 'httpd-access.log'),
      document_root=document_root,
      modules_dir=self.options['apache_modules_dir'],
      mime_types=self.options['apache_mime_file'],
      server_root=self.work_directory,
      email_address='admin@vifib.net',
      htpasswd_file=htpasswd_config['htpasswd_file'],
      ssl_certificate=ssl_config['certificate'],
      ssl_key=ssl_config['key'],
    )
    httpd_config_file = self.createConfigurationFile('httpd.conf',
      self.substituteTemplate(self.getTemplateFilename('httpd.conf.in'),
                              apache_config))
    self.path_list.append(httpd_config_file)
    apache_runner = zc.buildout.easy_install.scripts(
      [('httpd', 'slapos.recipe.librecipe.execute', 'execute')],
      self.ws, sys.executable, self.wrapper_directory,
      arguments=[self.options['apache_binary'],
                 '-f', httpd_config_file,
                 '-DFOREGROUND',
                ]
    )[0]
    self.path_list.append(apache_runner)
    return dict(ip=apache_config['ip'],
                port=apache_config['port'],
                user=htpasswd_config['user'],
                password=htpasswd_config['password']
               )

  def createHtpasswd(self):
    htpasswd = self.createConfigurationFile('htpasswd', '')
    self.path_list.append(htpasswd)
    password = self.generatePassword()
    user = 'user'
    subprocess.check_call([self.options['apache_htpasswd'],
                           '-bc', htpasswd,
                           user, password
                          ])
    return dict(htpasswd_file=htpasswd,
                user=user,
                password=password)

  def createCertificate(self, size=1024, subject='/C=FR/L=Marcq-en-Baroeul/O=Nexedi'):
    key_file = os.path.join(self.etc_directory, 'httpd.key')
    self.path_list.append(key_file)

    certificate_file = os.path.join(self.etc_directory, 'httpd.crt')
    self.path_list.append(certificate_file)

    subprocess.check_call([self.options['openssl_binary'],
                           'req', '-x509', '-nodes',
                           '-newkey', 'rsa:%s' % size,
                           '-subj', str(subject),
                           '-out', certificate_file,
                           '-keyout', key_file
                          ])
    return dict(key=key_file,
                certificate=certificate_file)
