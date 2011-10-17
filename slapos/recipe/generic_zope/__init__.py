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
  def install(self):
    """ Install a single Zope instance without ZEO Server.
    """
    path_list = []
    # Create zope configuration file
    zope_config = dict(
        products=self.options['products'],
        thread_amount=self.options['thread-amount'],
        zodb_root_path=self.options['zodb-path'],
        zodb_cache_size=self.options['zodb-cache-size'],
    )
    zope_environment = dict(
      TMP=self.options['tmp-path'],
      TMPDIR=self.options['tmp-path'],
      HOME=self.options['tmp-path'],
      PATH=self.options['bin-path']
    )
    # configure default Zope2 zcml
    open(self.options['site-zcml'], 'w').write(open(self.getTemplateFilename(
        'template/site.zcml')))
    zope_config['instance'] = self.options['instance-path']
    zope_config['event_log'] = self.options['event-log']
    zope_config['z2_log'] = self.options['z2-log']
    zope_config['pid-filename'] = self.options['pid-file']
    zope_config['lock-filename'] = self.options['lock-file']
    # XXX: !!killpidfromfile shall be binary provided by software!!
    killpidfromfile = self.createPythonScript('killpidfromfile',
        __name__ + '.killpidfromfile')
    path_list.append(killpidfromfile)

    post_rotate = self.createPythonScript(
      self.options['logrotate-post'],
      __name__ + '.killpidfromfile',
      [zope_config['pid-filename'], 'SIGUSR2']
    )
    path_list.append(post_rotate)
    prefixed_products = []
    for product in reversed(zope_config['products'].split()):
      product = product.strip()
      if product:
        prefixed_products.append('products %s' % product)
    prefixed_products.insert(0, 'products %s' % self.options[
      'instance-Products'])
    zope_config['products'] = '\n'.join(prefixed_products)
    zope_config['address'] = '%s:%s' % (self.options['ip'], self.options['port'])

    zope_wrapper_template_location = self.getTemplateFilename('zope.conf.in')
    self.options['deadlock-password'] = self.generatePassword()
    zope_conf_content = self.substituteTemplate(zope_wrapper_template_location,
      zope_config, dump_url=self.options['deadlock-path'],
      secret=self.options['deadlock-password'])

    zope_conf_path = self.createFile(self.options['configuration-file'], zope_conf_content)
    path_list.append(zope_conf_path)
    # Create init script
    path_list.append(self.createPythonScript(self.options['wrapper'], 'slapos.recipe.librecipe.execute.executee', [[self.options['runzope-binary'].strip(), '-C', zope_conf_path], zope_environment]))
    return path_list
