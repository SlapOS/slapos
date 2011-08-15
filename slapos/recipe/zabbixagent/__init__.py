##############################################################################
#
# Copyright (c) 2011 Vifib SARL and Contributors. All Rights Reserved.
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
import binascii
import os
import pkg_resources
import pprint
import hashlib
import sys
import zc.buildout
import zc.recipe.egg
import ConfigParser

class Recipe(BaseSlapRecipe):
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

  def registerLogRotation(self, name, log_file_list):
    """Register new log rotation requirement"""
    open(os.path.join(self.logrotate_d, name), 'w').write(
        pkg_resources.resource_string(__name__, 'template/logrotate_entry.in')%
          dict(file_list=' '.join(['"'+q+'"' for q in log_file_list]),
          olddir=self.logrotate_backup))

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
      self.wrapper_directory, arguments=[
        self.options['dcrond_binary'].strip(), '-s', cron_d, '-c', crontabs,
        '-t', timestamps, '-f', '-l', '5', '-M', catcher]
      )[0]
    self.path_list.append(wrapper)
    return cron_d

  def installZabbixAgentd(self, ip, port, hostname, server_ip,
                          user_parameter_string=''):
    log_file = os.path.join(self.log_directory, 'zabbix_agentd.log')
    self.registerLogRotation('zabbix_agentd', [log_file])

    zabbix_agentd_conf = dict(
      pid_file=os.path.join(self.run_directory, "zabbix_agentd.pid"),
      log_file=log_file,
      ip=ip,
      server=server_ip,
      hostname=hostname,
      port=port,
      user_parameter_string=user_parameter_string)

    zabbix_agentd_path = self.createConfigurationFile(
      "zabbix_agentd.conf",
      pkg_resources.resource_string(
        __name__, 'template/zabbix_agentd.conf.in') % zabbix_agentd_conf)

    self.path_list.append(zabbix_agentd_path)

    wrapper = zc.buildout.easy_install.scripts([('zabbixagentd',
      'slapos.recipe.librecipe.execute', 'execute')], self.ws, sys.executable,
      self.bin_directory, arguments=[
        self.options['zabbix_agentd_binary'].strip(), '-c',
        zabbix_agentd_path])[0]

    self.path_list.extend(zc.buildout.easy_install.scripts([
      ('zabbixagentd', __name__ + '.svcdaemon', 'svcdaemon')],
      self.ws, sys.executable, self.wrapper_directory, arguments=[dict(
        real_binary=wrapper, pid_file=zabbix_agentd_conf['pid_file'])]))

    return zabbix_agentd_conf

  def _install(self):
    self.path_list = []
    self.requirements, self.ws = self.egg.working_set()
    # self.cron_d is a directory, where cron jobs can be registered
    self.cron_d = self.installCrond()
    self.logrotate_d, self.logrotate_backup = self.installLogrotate()
    zabbix_agentd_conf = self.installZabbixAgentd(self.getGlobalIPv6Address(),
                                                  10050,
                                                  self.parameter_dict['hostname'],
                                                  self.parameter_dict['server'])
    self.setConnectionDict(dict(ip=zabbix_agentd_conf['ip'],
      name=zabbix_agentd_conf['hostname'], port=zabbix_agentd_conf['port']))
    return self.path_list
