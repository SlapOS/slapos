
import os, time
import shutil
import sys
import tempfile
import unittest
from slapos.slap.slap import NotFoundError

from slapos.recipe import re6stnet


class Re6stnetTest(unittest.TestCase):

  def setUp(self):
    self.ssl_dir = tempfile.mkdtemp()
    self.conf_dir = tempfile.mkdtemp()
    self.base_dir = tempfile.mkdtemp()
    self.token_dir = tempfile.mkdtemp()
    self.dir_list = [self.ssl_dir, self.conf_dir, self.base_dir, self.token_dir]
    config_file = os.path.join(self.base_dir, 'config')
    with open(config_file, 'w') as f:
      f.write('port  9201')
    self.options = options = {
                'openssl-bin': 'openssl',
                'key-file': os.path.join(self.ssl_dir, 'cert.key'),
                'cert-file': os.path.join(self.ssl_dir, 'cert.crt'),
                'key-size': '2048',
                'conf-dir': self.conf_dir,
                'token-dir': self.token_dir,
                'wrapper': os.path.join(self.base_dir, 'wrapper'),
                'config-file': config_file,
                'ipv4': '127.0.0.1',
                'port': '9201',
                'db-path': '/path/to/db',
                'command': '/path/to/command',
                'manager-wrapper': os.path.join(self.base_dir, 'manager_wrapper'),
                'drop-service-wrapper': os.path.join(self.base_dir, 'drop_wrapper'),
                'check-service-wrapper': os.path.join(self.base_dir, 'check_wrapper'),
                'slave-instance-list': '{}'
                }
    
  def tearDown(self):
    for path in self.dir_list:
      if os.path.exists(path):
        shutil.rmtree(path)
    
  def new_recipe(self):
      buildout = {
              'buildout': {
                  'bin-directory': '',
                  'find-links': '',
                  'allow-hosts': '',
                  'develop-eggs-directory': '',
                  'eggs-directory': '',
                  'python': 'testpython',
                  },
               'testpython': {
                   'executable': sys.executable,
                   },
               'slap-connection': {
                   'computer-id': '',
                   'partition-id': '',
                   'server-url': '',
                   'software-release-url': '',
                   }
              }

      options = self.options

      return re6stnet.Recipe(buildout=buildout, name='re6stnet', options=options)
  
  def test_generateCertificates(self):
    
    self.options['ipv6-prefix'] = '2001:db8:24::/48'
    self.options['key-size'] = '2048'
    
    recipe = self.new_recipe()
    
    recipe.generateCertificate()
    
    self.assertTrue(os.path.exists(self.options['key-file']))
    self.assertTrue(os.path.exists(self.options['cert-file']))
    
    last_time = time.ctime(os.stat(self.options['key-file'])[7])
    
    recipe.generateCertificate()
    
    self.assertTrue(os.path.exists(self.options['key-file']))
    this_time = time.ctime(os.stat(self.options['key-file'])[7])
    
    self.assertEqual(last_time, this_time)
  
  def test_generateCertificates_other_ipv6(self):
    
    self.options['ipv6-prefix'] = 'be28:db8:fe6a:d85:4fe:54a:ae:aea/64'
    
    recipe = self.new_recipe()
    
    recipe.generateCertificate()
    
    self.assertTrue(os.path.exists(self.options['key-file']))
    self.assertTrue(os.path.exists(self.options['cert-file']))

  def test_install(self):
    recipe = self.new_recipe()

    recipe.options.update({
        'ipv6-prefix': '2001:db8:24::/48',
        'slave-instance-list': '''[
            {"slave_reference":"SOFTINST-58770"},
            {"slave_reference":"SOFTINST-58778"}
            ]
            '''
        })

    try:
      recipe.install()
    except NotFoundError:
      # Recipe will raise not found error when trying to publish slave informations
      pass
    
    self.assertItemsEqual(os.listdir(self.ssl_dir),
                          ['cert.key', 'cert.crt'])
    
    token_file = os.path.join(self.options['conf-dir'], 'token.json')
    self.assertTrue(os.path.exists(token_file))
    
    # token file must contain 2 elements
    token_content = recipe.readFile(token_file)
    self.assertIn('SOFTINST-58770', token_content)
    self.assertIn('SOFTINST-58778', token_content)
    
    token_dict = recipe.loadJsonFile(token_file)
    self.assertEqual(len(token_dict), 2)
    self.assertTrue(token_dict.has_key('SOFTINST-58770'))
    self.assertTrue(token_dict.has_key('SOFTINST-58778'))
        
    self.assertItemsEqual(os.listdir(self.token_dir),
                          ['SOFTINST-58770.add', 'SOFTINST-58778.add'])

    first_add = recipe.readFile(os.path.join(self.token_dir, 'SOFTINST-58770.add'))
    self.assertEqual(token_dict['SOFTINST-58770'], first_add)
    
    second_add = recipe.readFile(os.path.join(self.token_dir, 'SOFTINST-58778.add'))
    self.assertEqual(token_dict['SOFTINST-58778'], second_add)
    
    # Remove one element
    recipe.options.update({
        "slave-instance-list": """[{"slave_reference":"SOFTINST-58770"}]"""
        })
    try:
      recipe.install()
    except NotFoundError:
      # Recipe will raise not found error when trying to publish slave informations
      pass
    token_dict = recipe.loadJsonFile(token_file)
    
    self.assertEqual(len(token_dict), 1)
    self.assertEqual(token_dict['SOFTINST-58770'], first_add)
    self.assertItemsEqual(os.listdir(self.token_dir),
                          ['SOFTINST-58770.add', 'SOFTINST-58778.remove'])
    
    second_remove = recipe.readFile(os.path.join(self.token_dir, 'SOFTINST-58778.remove'))
    self.assertEqual(second_add, second_remove)
  
  def test_install_empty_slave(self):
    recipe = self.new_recipe()

    recipe.options.update({
        'ipv6-prefix': '2001:db8:24::/48'
        })

    recipe.install()
    
    self.assertItemsEqual(os.listdir(self.ssl_dir),
                          ['cert.key', 'cert.crt'])
    
    token_file = os.path.join(self.options['conf-dir'], 'token.json')
    self.assertTrue(os.path.exists(token_file))
    
    token_content = recipe.readFile(token_file)
    self.assertEqual(token_content, '{}')
    self.assertItemsEqual(os.listdir(self.options['token-dir']), [])

