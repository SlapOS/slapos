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

from slapos.recipe.librecipe import GenericBaseRecipe
import os
import sys
import urlparse

class Recipe(GenericBaseRecipe):
  """
  Instanciate ERP5 in Zope

  Input:
    mysql-url
      mysql url, must contain connexion informations.    

    zope-url (optional)
      Url of zope, this url will be parsed to get these values:
      protocol://username@password:hostname:port/site_id

    If specified following inputs have priority on parsed zope-url values:
    zope-hostname (optional)
      Zope hostname.
      Default value: "localhost", if not contained in zope-url.
    zope-port (optional)
      Zope port.
      Default value: "80", if not contained in zope-url.
    zope-protocol (optional)
      Protocol used.
      Default "http" if not contained in zope-url.
    zope-password (optional)
      Zope user password.
      Default value: "insecure", if not contained in zope-url.
    zope-username (optional)
      Zope username.
      Default value: "zope", if not contained in zope-url.
    site-id (optional)
      Site id
      ex: erp5
      Default value: "erp5", if not contained in zope-url.

    runner-path
      The path to create the runner.

    scalability (optional)
      Boolean, default value: "False"
      If true erp5 site will fix the site consistency and
      will use configurator to automaticlly install a
      small and medium buisiness. 
  """

  def install(self):
    parsed = urlparse.urlparse(self.options['mysql-url'])
    mysql_connection_string = "%(database)s@%(hostname)s:%(port)s "\
        "%(username)s %(password)s" % dict(
      database=parsed.path.split('/')[1],
      hostname=parsed.hostname,
      port=parsed.port,
      username=parsed.username,
      password=parsed.password
    )

    # Init zope configuration
    zope_username = None
    zope_password = None    
    zope_hostname = None
    zope_port = None
    zope_protocol = None

    # Get informations from zope url
    if self.options.get('zope-url'):
      zope_parsed = urlparse.urlparse(self.options['zope-url'])
    # Zope hostname
    if self.options.get('zope-hostname'):
      zope_hostname = self.options['zope-hostname']
    elif self.options.get('zope-url'):
      zope_hostname = zope_parsed.hostname
    else:
      zope_hostname = 'localhost'
    # Zope port
    if self.options.get('zope-port'):
      zope_port = self.options['zope-port']
    elif self.options.get('zope-url'):
      zope_port = zope_parsed.port
    else:
      zope_port = 8080
    # Zope username and password
    if self.options.get('zope-username') and self.options.get('zope-password'):
      zope_username = self.options['zope-username']
      zope_password = self.options['zope-password']
    elif self.options.get('zope-url'):
      zope_username = zope_parsed.username
      zope_password = zope_parsed.password
    else:
      zope_username = 'zope'
      zope_password = 'insecure'
    # Zope protocol
    if self.options.get('zope-protocol'):
      zope_protocol = self.options['zope-protocol']
    elif self.options.get('zope-url'):
      zope_protocol = zope_parsed.scheme      
    else:
      zope_protocol = 'http'
    # Zope site-id
    if self.options.get('zope-site-id'):
      zope_site_id = self.options['zope-site-id']
    elif self.options.get('zope-url'):
      zope_site_id = zope_parsed.path.split('/')[1],
    else:
      zope_site_id = 'erp5'

    config = dict(
      python_path=sys.executable,
      user=zope_username,
      password=zope_password,
      site_id=zope_site_id,
      host="%s:%s" % (zope_hostname, zope_port),
      protocol=zope_protocol,
      sql_connection_string=mysql_connection_string,
      scalability=self.options.get('scalability', 'False'),
    )

    # Runners
    runner_path = self.createExecutable(
      self.options['runner-path'],
      self.substituteTemplate(self.getTemplateFilename('erp5_bootstrap.in'),
                              config))

    return [runner_path]
