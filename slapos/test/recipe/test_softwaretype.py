import os
import mock
import shutil
import sys
import tempfile
import unittest

from slapos.recipe import softwaretype


class SoftwareTypeTest(unittest.TestCase):

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
                     },
                 # XXX softwaretype still uses slap_connection
                 'slap_connection': {
                     'computer_id': '',
                     'partition_id': '',
                     'server_url': '',
                     'software_release_url': '',
                     }
                }
        options = { }
        return softwaretype.Recipe(buildout=buildout, name='softwaretype', options=options)

    def setUp(self):
        self.recipe = self.new_recipe()

    def _mockComputerPartition(self):
        class MockComputerPartition(object):
            _requested_state = 'installed'
            def getInstanceParameterDict(self):
                return {
                    'slap_software_type': 'test',
                    'ip_list': [
                        ('lo', '127.0.0.1',),
                        ('lo', '::1',),
                    ]
                }
        return MockComputerPartition()

    @mock.patch('slapos.slap.slap.registerComputerPartition')
    def test_install(self, mock_client):
        mock_client.return_value = self._mockComputerPartition()

        buildout_directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, buildout_directory)
        instance_buildout_file = os.path.join(buildout_directory, 'instance-test.cfg')
        with open(instance_buildout_file, 'w') as software_type_buildout:
            software_type_buildout.write('''
[buildout]
parts = test

[test]
recipe = plone.recipe.command
command = touch file_created_when_running_instance
''')

        self.recipe.buildout['buildout']['directory'] = buildout_directory
        # we use software_type "test", so buildout will be executed using instance-test.cfg
        self.recipe.options['test'] = instance_buildout_file

        # recipe reuse sys.argv to call the same buildout that its being running in
        # but here we are not runing buildout, so we fake sys.argv
        sys.argv = ['buildout', ]

        self.recipe.install()

        self.assertItemsEqual(
            os.listdir(buildout_directory),
            [
            # standard buildout files
             'instance-test.cfg',
             'buildout-softwaretype.cfg',
             'eggs',
             'bin',
             'parts',
             'develop-eggs',
             '.installed-softwaretype.cfg',

             # the file we touch in the test to proove buildout has been running
             'file_created_when_running_instance',
        ])


