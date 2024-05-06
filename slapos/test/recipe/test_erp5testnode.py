import functools
import os
import shutil
import tempfile
import unittest

from six.moves import configparser
import zc.buildout.testing


class UserInfoTest(unittest.TestCase):
  def setUp(self):
    self.tmp_dir = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.tmp_dir)

    self.get_temp_path = functools.partial(os.path.join, self.tmp_dir)

    self.buildout = buildout = zc.buildout.testing.Buildout()
    buildout['slap-connection'] = {
        'computer-id': 'computer-id',
        'server-url': 'https://slapos.example.com',
    }
    # dummy defaults
    buildout['erp5testnode'] = {
        'apache-binary': '/bin/httpd',
        'apache-htpasswd': '/bin/htpasswd',
        'apache-mime-file': '/etc/mime.types',
        'apache-modules-dir': '/srv/modules',
        'frontend-url': 'https://example.com/',
        'git-binary': '/bin/git',
        'httpd-cert-file': 'etc/httpd-public.crt',
        'httpd-key-file': 'etc/httpd-public.key',
        'httpd-conf-file': 'etc/httpd.conf',
        'httpd-ip': '::1',
        'httpd-lock-file': 'var/run/httpd.lock',
        'httpd-log-directory': 'var/log',
        'httpd-pid-file': 'var/run/httpd.pid',
        'httpd-port': '9080',
        'httpd-software-access-port': '9081',
        'httpd-software-directory': 'srv/software',
        'httpd-wrapper': 'bin/httpd',
        'instance-dict': '',
        'ipv4-address': '127.0.0.1',
        'ipv6-address': '::1',
        'keep-log-days': '3',
        'log-directory': 'var/log/testnode',
        'log-file': 'var/log/erp5testnode.log',
        'log-frontend-url': 'https://example.com',
        'node-quantity': '2',
        'proxy-host': '127.0.0.1',
        'proxy-port': '5000',
        'recipe': 'slapos.cookbook:erp5testnode',
        'run-directory': 'var/run/testnode',
        'shared-part-list': 'srv/shared',
        'slapos-binary': '/bin/slapos',
        'slapos-directory': 'srv/slapos',
        'software-directory': 'srv/software',
        'software-path-list': '[""]',
        'srv-directory': 'srv',
        'test-node-title': 'TEST NODE TITLE',
        'test-suite-directory': 'srv/test_suite',
        'test-suite-master-url': 'https://testnode.example.com',
        'testnode': '/bin/testnode',
        'working-directory': 'srv/testnode',
        'wrapper': 'bin/erp5testnode-service',
    }

    # values for test
    buildout['erp5testnode']['configuration-file'] = self.get_temp_path(
        'configuration-file')
    buildout['erp5testnode']['wrapper'] = self.get_temp_path('wrapper')
    buildout['erp5testnode']['httpd-conf-file'] = self.get_temp_path(
        'httpd-conf-file')
    buildout['erp5testnode']['httpd-wrapper'] = self.get_temp_path(
        'httpd-wrapper')

    buildout['erp5testnode']['log-directory'] = self.get_temp_path(
        'log-directory')
    os.mkdir(self.get_temp_path('log-directory'))
    # software URLs are given as a json encoded string
    buildout['erp5testnode'][
        'software-path-list'] = '["https://example.com/slapos/software.cfg", "https://example.com/slapos/another-software.cfg"]'

    from slapos.recipe import erp5testnode
    self.recipe = erp5testnode.Recipe(
        buildout,
        'erp5testnode',
        buildout['erp5testnode'],
    )

  def test_installed_paths(self):
    self.assertEqual(
        sorted(self.recipe.install()),
        sorted([
            self.get_temp_path('configuration-file'),
            self.get_temp_path('wrapper'),
            self.get_temp_path('httpd-conf-file'),
            self.get_temp_path('httpd-wrapper'),
        ]))

  def test_configuration_file(self):
    self.recipe.install()

    parser = configparser.ConfigParser()
    parser.read(self.get_temp_path('configuration-file'))

    # this is generally a valid configparser file.
    self.assertEqual(parser.get('testnode', 'slapos_directory'), 'srv/slapos')

    # software URLs are specified comma separated (XXX not sure it was
    # good idea, but it's like this)
    self.assertEqual(parser.get('software_list', 'path_list'),
      "https://example.com/slapos/software.cfg,https://example.com/slapos/another-software.cfg")


  def test_log_directory_apache(self):
    self.recipe.install()

    self.assertTrue(
        os.path.exists(self.get_temp_path('log-directory', 'index.html')))

    # apache to expose log directory
    with open(self.get_temp_path('httpd-conf-file')) as f:
      self.assertIn(
          'DocumentRoot "{}"'.format(self.get_temp_path('log-directory')),
          f.read())

    # wrapper references the config file
    with open(self.get_temp_path('httpd-wrapper')) as f:
      self.assertIn(self.get_temp_path('httpd-conf-file'), f.read())
