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
import ConfigParser
import json
import os
import StringIO

from slapos.recipe.librecipe import GenericBaseRecipe

class Recipe(GenericBaseRecipe):
  def install(self):
    self.path_list = []
    options = self.options.copy()
    del options['recipe']
    CONFIG = {k.replace('-', '_'): v for k, v in options.iteritems()}
    CONFIG['PATH'] = os.environ['PATH']

    if self.options['instance-dict']:
      config_instance_dict = ConfigParser.ConfigParser()
      config_instance_dict.add_section('instance_dict')
      instance_dict = json.loads(self.options['instance-dict'])

      for k ,v in instance_dict.iteritems():
        config_instance_dict.set('instance_dict', k, v)
      value = StringIO.StringIO()
      config_instance_dict.write(value)
      CONFIG['instance_dict'] = value.getvalue()

    software_path_list = json.loads(self.options['software-path-list'])
    CONFIG["software_path_list"] = ""
    if software_path_list:
      CONFIG["software_path_list"] = "[software_list]"
      CONFIG["software_path_list"] += \
          "\npath_list = %s" % ",".join(software_path_list) 
    CONFIG['computer_id'] = self.buildout['slap-connection']['computer-id']
    CONFIG['server_url'] = self.buildout['slap-connection']['server-url']
    configuration_file = self.createFile(
      self.options['configuration-file'],
      self.substituteTemplate(
        self.getTemplateFilename('erp5testnode.cfg.in'),
        CONFIG
      ),
    )
    self.path_list.append(configuration_file)
    self.path_list.append(
      self.createPythonScript(
        self.options['wrapper'],
        'slapos.recipe.librecipe.execute.executee',
        [ # Executable
          [ self.options['testnode'], '-l', self.options['log-file'],
            configuration_file],
          # Environment
          {
            'GIT_SSL_NO_VERIFY': '1',
          }
        ],
      )
    )
    self.installApache()
    return self.path_list

  def installApache(self):
    apache_config = dict(
        pid_file=self.options['httpd-pid-file'],
        lock_file=self.options['httpd-lock-file'],
        ip=self.options['httpd-ip'],
        port=self.options['httpd-port'],
        software_access_port=self.options['httpd-software-access-port'],
        testnode_srv_directory=self.options['srv-directory'],
        error_log=os.path.join(self.options['httpd-log-directory'],
                               'httpd-error.log'),
        access_log=os.path.join(self.options['httpd-log-directory'],
                                'httpd-access.log'),
        certificate=self.options['httpd-cert-file'],
        key=self.options['httpd-key-file'],
        testnode_log_directory=self.options['log-directory'],
        testnode_software_directory=self.options['software-directory'],
    )
    config_file = self.createFile(self.options['httpd-conf-file'],
       self.substituteTemplate(self.getTemplateFilename('httpd.conf.in'),
                               apache_config)
    )
    self.path_list.append(config_file)
    wrapper = self.createPythonScript(self.options['httpd-wrapper'],
      'slapos.recipe.librecipe.execute.execute',
      [self.options['apache-binary'], '-f', config_file, '-DFOREGROUND'])
    self.path_list.append(wrapper)
    # create empty html page to not allow listing of /
    page = open(os.path.join(self.options['log-directory'], "index.html"), "w")
    page.write("<html/>")
    page.close()
