
import os, time
import shutil
import sys
import tempfile
import unittest
from slapos.slap.slap import NotFoundError, ConnectionError

import six


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
                'openssl-bin': '/usr/bin/openssl',
                'key-file': os.path.join(self.ssl_dir, 'cert.key'),
                'cert-file': os.path.join(self.ssl_dir, 'cert.crt'),
                'dh-file': os.path.join(self.ssl_dir, 'dh.pem'),
                'key-size': '2048',
                'conf-dir': self.conf_dir,
                'token-dir': self.token_dir,
                'wrapper': os.path.join(self.base_dir, 'wrapper'),
                'config-file': config_file,
                'ipv4': '127.0.0.1',
                'port': '9201',
                'pid-file': '/path/to/pid/file',
                'command': '/path/to/command',
                'manager-wrapper': os.path.join(self.base_dir, 'manager_wrapper'),
                'drop-service-wrapper': os.path.join(self.base_dir, 'drop_wrapper'),
                'check-service-wrapper': os.path.join(self.base_dir, 'check_wrapper'),
                'revoke-service-wrapper': os.path.join(self.base_dir, 'revoke_wrapper'),
                'slave-instance-list': '{}'
                }
    
  def tearDown(self):
    for path in self.dir_list:
      if os.path.exists(path):
        shutil.rmtree(path)
    
  def new_recipe(self):
      from slapos.recipe import re6stnet
      from slapos.test.utils import makeRecipe
      return makeRecipe(
            re6stnet.Recipe,
            options=self.options,
            slap_connection={
                   'computer-id': 'comp-test',
                   'partition-id': 'slappart0',
                   'server-url': 'http://server.com',
                   'software-release-url': 'http://software.com',
                   'key-file': '/path/to/key',
                   'cert-file': '/path/to/cert'
            },
            name='re6stnet')


  def checkWrapper(self, path):
    self.assertTrue(os.path.exists(path))
    content = ""
    token_file = os.path.join(self.options['conf-dir'], 'token.json')
    with open(path, 'r') as f:
        content = f.read()
    self.assertIn("('http://%s:%s/', %r, %r," % (
      self.options['ipv4'], self.options['port'], self.token_dir, token_file),
      content)
    self.assertIn("'partition_id': 'slappart0'", content)
    self.assertIn("'computer_guid': 'comp-test'", content)
    self.assertIn("'key_file': '/path/to/key'", content)
    self.assertIn("'cert_file': '/path/to/cert'", content)
    self.assertIn("'master_url': 'http://server.com'", content)
  
  def fake_generateCertificates(self):
    return

  def test_generateCertificates(self):
    
    self.options['ipv6-prefix'] = '2001:db8:24::/48'
    self.options['key-size'] = '2048'
    
    recipe = self.new_recipe()
    
    recipe.generateCertificate()
    
    six.assertCountEqual(self, os.listdir(self.ssl_dir),
                          ['cert.key', 'cert.crt', 'dh.pem'])
    
    last_time = time.ctime(os.stat(self.options['key-file'])[7])

    recipe.generateCertificate()

    self.assertTrue(os.path.exists(self.options['key-file']))
    this_time = time.ctime(os.stat(self.options['key-file'])[7])

    self.assertEqual(last_time, this_time)
  
  def test_getSerialFromIpv6(self):

    ipv6 = 'be28:db8:fe6a:d85:4fe:54a:ae:aea/64'

    recipe = self.new_recipe()
    serial = recipe.getSerialFromIpv6(ipv6)

    self.assertEqual(serial, '0x1be280db8fe6a0d8504fe054a00ae0aea')

    ipv6 = '2001:db8:24::/48'
    serial = recipe.getSerialFromIpv6(ipv6)

    self.assertEqual(serial, '0x120010db80024')

  def test_install(self):
    self.options.update({
        'ipv6-prefix': '2001:db8:24::/48',
        'slave-instance-list': '''[
            {"slave_reference":"SOFTINST-58770"},
            {"slave_reference":"SOFTINST-58778"}
            ]
            '''
        })

    recipe = self.new_recipe()
    recipe.generateCertificate = self.fake_generateCertificates

    try:
      recipe.install()
    except (NotFoundError, ConnectionError):
      # Recipe will raise not found error when trying to publish slave informations
      pass
    
    token_file = os.path.join(self.options['conf-dir'], 'token.json')
    self.assertTrue(os.path.exists(token_file))
    
    # token file must contain 2 elements
    token_content = recipe.readFile(token_file)
    self.assertIn('SOFTINST-58770', token_content)
    self.assertIn('SOFTINST-58778', token_content)
    
    token_dict = recipe.loadJsonFile(token_file)
    self.assertEqual(len(token_dict), 2)
    self.assertIn('SOFTINST-58770', token_dict)
    self.assertIn('SOFTINST-58778', token_dict)
        
    six.assertCountEqual(self, os.listdir(self.token_dir),
                          ['SOFTINST-58770.add', 'SOFTINST-58778.add'])

    first_add = recipe.readFile(os.path.join(self.token_dir, 'SOFTINST-58770.add'))
    self.assertEqual(token_dict['SOFTINST-58770'], first_add)
    
    second_add = recipe.readFile(os.path.join(self.token_dir, 'SOFTINST-58778.add'))
    self.assertEqual(token_dict['SOFTINST-58778'], second_add)
    
    self.checkWrapper(os.path.join(self.base_dir, 'manager_wrapper'))
    
    # Remove one element
    self.options.update({
        "slave-instance-list": """[{"slave_reference":"SOFTINST-58770"}]"""
        })
    recipe = self.new_recipe()
    recipe.generateCertificate = self.fake_generateCertificates

    try:
      recipe.install()
    except (NotFoundError, ConnectionError):
      # Recipe will raise not found error when trying to publish slave informations
      pass
    token_dict = recipe.loadJsonFile(token_file)
    
    self.assertEqual(len(token_dict), 1)
    self.assertEqual(token_dict['SOFTINST-58770'], first_add)
    six.assertCountEqual(self, os.listdir(self.token_dir),
                          ['SOFTINST-58770.add', 'SOFTINST-58778.remove'])
    
    second_remove = recipe.readFile(os.path.join(self.token_dir, 'SOFTINST-58778.remove'))
    self.assertEqual(second_add, second_remove)
  
  def test_install_empty_slave(self):
    self.options.update({
        'ipv6-prefix': '2001:db8:24::/48'
        })
    recipe = self.new_recipe()
    recipe.generateCertificate = self.fake_generateCertificates

    recipe.install()

    token_file = os.path.join(self.options['conf-dir'], 'token.json')
    self.assertTrue(os.path.exists(token_file))
    
    token_content = recipe.readFile(token_file)
    self.assertEqual(token_content, '{}')
    six.assertCountEqual(self, os.listdir(self.options['token-dir']), [])

    self.checkWrapper(os.path.join(self.base_dir, 'manager_wrapper'))

