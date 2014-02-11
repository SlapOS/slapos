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
from slapos.recipe.librecipe import GenericBaseRecipe

class Recipe(GenericBaseRecipe):
  """
  haproxy instance configuration.

  name -- local name of the haproxy

  wrapper-path -- location of the init script to generate

  binary-path -- location of the haproxy command

  ctl-path -- location of the haproxy control script

  conf-path -- location of the configuration file

  socket-path -- location of the socket file for administration

  ip -- ip of the haproxy server

  port -- port of the haproxy server

  server-check-path -- path of the domain to check

  address -- string with list of all url to check
    Example: 127.0.0.1:12004 127.0.0.1:12005
  """

  def install(self):
    # inter must be quite short in order to detect quickly an unresponsive node
    #      and to detect quickly a node which is back
    # rise must be minimal possible : 1, indeed, a node which is back don't need
    #      to sleep more time and we can give him work immediately
    # fall should be quite sort. with inter at 3, and fall at 2, a node will be
    #      considered as dead after 6 seconds.
    # maxconn should be set as the maximum thread we have per zope, like this
    #      haproxy will manage the queue of request with the possibility to
    #      move a request to another node if the initially selected one is dead
    # maxqueue is the number of waiting request in the queue of every zope client.
    #      It allows to make sure that there is not a zope client handling all
    #      the work while other clients are doing nothing. This was happening
    #      even thoug we have round robin distribution because when a node dies
    #      some seconds, all request are dispatched to other nodes, and then users
    #      stick in other nodes and are not coming back. Please note this option
    #      is not an issue if you have more than (maxqueue * node_quantity) requests
    #      because haproxy will handle a top-level queue
    try:
      backend_dict = self.options['backend-dict']
    except KeyError:
      backend_list = self.options['backend-list']
      if isinstance(backend_list, str):
        # BBB
        backend_list = backend_list.split()
      backend_dict = {
        self.options['name']: (self.options['port'], backend_list),
      }

    server_snippet_filename = self.getTemplateFilename(
      'haproxy-server-snippet.cfg.in')
    listen_snippet_filename = self.getTemplateFilename(
      'haproxy-listen-snippet.cfg.in')
    server_snippet = ""
    ip = self.options['ip']
    server_check_path = self.options.get('server-check-path', None)
    if server_check_path:
      httpchk = 'option httpchk GET %s' % server_check_path
    else:
      httpchk = ''
    # FIXME: maxconn must be provided per-backend, not globally
    maxconn = self.options['maxconn']
    i = 0
    for name, (port, backend_list) in backend_dict.iteritems():
      server_snippet += self.substituteTemplate(
        listen_snippet_filename, {
          'name': name,
          'ip': ip,
          'port': port,
          'httpchk': httpchk,
        })
      for address in backend_list:
        i += 1
        server_snippet += self.substituteTemplate(
          server_snippet_filename, {
            'name': '%s_%s' % (name, i),
            'address': address,
            'cluster_zope_thread_amount': maxconn,
          })

    configuration_path = self.createFile(
      self.options['conf-path'],
      self.substituteTemplate(
        self.getTemplateFilename('haproxy.cfg.in'),
        {'socket_path': self.options['socket-path'],
         'server_text': server_snippet},
      )
    )
    wrapper_path = self.createPythonScript(
      self.options['wrapper-path'],
      'slapos.recipe.librecipe.execute.execute',
      arguments=[self.options['binary-path'].strip(), '-f', configuration_path],)
    ctl_path = self.createPythonScript(
      self.options['ctl-path'],
      '%s.haproxy.haproxyctl' % __name__,
      {'socket_path':self.options['socket-path']})
    return [configuration_path, wrapper_path, ctl_path]
