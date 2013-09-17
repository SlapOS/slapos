##############################################################################
#
# Copyright (c) 2012 Vifib SARL and Contributors. All Rights Reserved.
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
import os
import re
from slapos.recipe.librecipe import GenericSlapRecipe

class Recipe(GenericSlapRecipe):
  """
    Instantiate varnish daemon

    TODO:
      - use varnish3.x and replace .vcl for it
  """
  def _install(self):
    ip = self.options['ip']
    backend_url = self.options.get('backend-url',
      # BBB: Peeking in partition parameters directly. Eew.
      self.parameter_dict.get('backend-url',
        self.parameter_dict.get('tidstorage-url') # BBB
      )
    )
    backend_server, backend_port = self._getBackendServer(backend_url)
    path_list = []
    if backend_url.startswith('https://'):
      config = dict(
        stunnel_binary=self.options['stunnel-binary'],
        stunnel_server=ip,
        stunnel_port=int(self.options['stunnel-port']),
        stunnel_pid_file=self.options['stunnel-pid-file'],
        stunnel_conf_file=self.options['stunnel-conf-file'],
        shell_path=self.options['shell-path'],
        backend_server=backend_server.replace('[', '').replace(']', ''),
        backend_port=backend_port,
      )
      path_list.append(self.createExecutable(self.options['stunnel-wrapper'],
        self.substituteTemplate(self.getTemplateFilename('stunnel.in'),
          config)))
      path_list.append(self.createFile(self.options['stunnel-conf-file'],
        self.substituteTemplate(self.getTemplateFilename('stunnel.conf.in'),
          config)))
      backend_server = ip
      backend_port = int(self.options['stunnel-port'])
    varnishd_manager_port = int(self.options['manager-port'])
    varnishd_server_port = int(self.options['server-port'])
    config = dict(
      varnishd_binary=self.options['varnishd-binary'],
      varnish_ip=ip,
      varnishlog_binary=self.options['varnishlog-binary'],
      varnishd_manager_port=varnishd_manager_port,
      varnishd_server_port=varnishd_server_port,
      varnishd_pid_file=self.options['pid-file'],
      varnish_instance_name=self.options['varnish-instance-name'],
      varnish_data=self.options['varnish-data'],
      gcc_location=self.options['gcc-location'],
      shell_path=self.options['shell-path'],
      vcl_file=self.options['vcl-file'],
      backend_port=backend_port,
      backend_server=backend_server,
    )

    path_list.append(self.createExecutable(self.options['varnishd-wrapper'],
      self.substituteTemplate(self.getTemplateFilename('varnishd.in'),
        config)))
    path_list.append(self.createExecutable(self.options['varnishlog-wrapper'],
      self.substituteTemplate(self.getTemplateFilename('varnishlog.in'),
        config)))
    path_list.append(self.createFile(self.options['vcl-file'],
      self.substituteTemplate(self.getTemplateFilename('default.vcl.in'),
        config)))
    return path_list

  def _getBackendServer(self, url):
    r = re.compile('\/\/(\[.+\]|[\d.]+):(\d*)')
    result = r.search(url)
    ip = result.groups()[0]
    port = result.groups()[1]
    return (ip, port)
