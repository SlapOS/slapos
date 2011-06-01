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
from slapos.lib.recipe.BaseSlapRecipe import BaseSlapRecipe
import os
import pkg_resources
import sys
import zc.buildout
import zc.recipe.egg

class Recipe(BaseSlapRecipe):
  def getTemplateFilename(self, template_name):
    return pkg_resources.resource_filename(__name__,
        'template/%s' % template_name)

  def _install(self):
    self.path_list = []
    self.requirements, self.ws = self.egg.working_set([__name__])
    # self.cron_d is a directory, where cron jobs can be registered
    self.cron_d = self.installCrond()
    self.logrotate_d, self.logrotate_backup = self.installLogrotate()
    # Use killpidfromfile from ERP5.
    self.killpidfromfile = zc.buildout.easy_install.scripts(
        [('killpidfromfile', __name__ + 'slapos.recipe.erp5.killpidfromfile',
          'killpidfromfile')], self.ws, sys.executable, self.bin_directory)[0]
    self.path_list.append(self.killpidfromfile)
    
    kumo_conf = self.installKumo(self.getLocalIPv4Address())

    self.linkBinary()
    self.setConnectionDict(dict(
      address = kumo_conf['kumo_address'],
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
    wrapper = zc.buildout.easy_install.scripts([('crond',
      __name__ + '.execute', 'execute')], self.ws, sys.executable,
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
  
  def installKumo(self, ip, kumo_manager_port=13101, kumo_server_port=13201,
      kumo_server_listen_port=13202, kumo_gateway_port=13301):
    # XXX: kumo is not storing pid in file, unless it is not running as daemon
    #      but running daemons is incompatible with SlapOS, so there is currently
    #      no way to have Kumo's pid files to rotate logs and send signals to them
    config = dict(
      kumo_gateway_binary=self.options['kumo_gateway_binary'],
      kumo_gateway_ip=ip,
      kumo_gateway_log=os.path.join(self.log_directory, "kumo-gateway.log"),
      kumo_manager_binary=self.options['kumo_manager_binary'],
      kumo_manager_ip=ip,
      kumo_manager_log=os.path.join(self.log_directory, "kumo-manager.log"),
      kumo_server_binary=self.options['kumo_server_binary'],
      kumo_server_ip=ip,
      kumo_server_log=os.path.join(self.log_directory, "kumo-server.log"),
      kumo_server_storage=os.path.join(self.data_root_directory, "kumodb.tch"),
      kumo_manager_port=kumo_manager_port,
      kumo_server_port=kumo_server_port,
      kumo_server_listen_port=kumo_server_listen_port,
      kumo_gateway_port=kumo_gateway_port
    )

    self.path_list.append(self.createRunningWrapper('kumo_gateway',
      self.substituteTemplate(self.getTemplateFilename('kumo_gateway.in'),
        config)))

    self.path_list.append(self.createRunningWrapper('kumo_manager',
      self.substituteTemplate(self.getTemplateFilename('kumo_manager.in'),
        config)))

    self.path_list.append(self.createRunningWrapper('kumo_server',
      self.substituteTemplate(self.getTemplateFilename('kumo_server.in'),
        config)))

    return dict(
      kumo_address = '%s:%s' % (config['kumo_gateway_ip'],
        config['kumo_gateway_port']),
      kumo_gateway_ip=config['kumo_gateway_ip'],
      kumo_gateway_port=config['kumo_gateway_port'],
    )