
import os
import shutil
import sys
import tempfile
import unittest
import six

if six.PY2:
  unittest.TestCase.assertRaisesRegex = unittest.TestCase.assertRaisesRegexp

class PBSTest(unittest.TestCase):
    def new_recipe(self):
        from slapos.recipe import pbs
        from slapos.test.utils import makeRecipe
        options = {
            'restic-binary': '',
            'restic-rest-server-binary': '',
        }
        return makeRecipe(
            pbs.Recipe,
            options=options,
            name='pbs')

    def test_push(self):
        recipe = self.new_recipe()

        with tempfile.NamedTemporaryFile('w+') as restic_wrapper:
            recipe.wrapper_push(remote_schema='TEST_REMOTE_SCHEMA',
                                local_dir='TEST_LOCAL_DIR',
                                remote_dir='TEST_REMOTE_PARENT/TEST_REMOTE_DIR',
                                restic_wrapper_path=restic_wrapper.name)
            content = open(restic_wrapper.name, 'r').read()
            self.assertIn('TEST_REMOTE_SCHEMA -R $SSH_CLIENT_SOCKET:$RESTIC_REST_SERVER_SOCKET', content)
            self.assertIn('TEST_LOCAL_DIR', content)
            self.assertIn('TEST_REMOTE_PARENT/restic.sock', content)

    def test_pull(self):
        recipe = self.new_recipe()

        with tempfile.NamedTemporaryFile('w+') as restic_wrapper:
            recipe.wrapper_pull(remote_schema='TEST_REMOTE_SCHEMA',
                                local_dir='TEST_LOCAL_DIR',
                                remote_dir='TEST_REMOTE_PARENT/TEST_REMOTE_DIR',
                                restic_wrapper_path=restic_wrapper.name,
                                remove_backup_older_than='2W')
            content = open(restic_wrapper.name, 'r').read()
            self.assertIn('TEST_REMOTE_SCHEMA -R $SSH_CLIENT_SOCKET:$RESTIC_REST_SERVER_SOCKET', content)
            self.assertIn('TEST_LOCAL_DIR', content)
            self.assertIn('TEST_REMOTE_PARENT', content)
            self.assertIn('--keep-within 14d', content)

    def test_invalid_type(self):
        recipe = self.new_recipe()

        entry = {
                'url': 'http://url.to.something/',
                'type': 'invalid'
                }

        self.assertRaisesRegex(ValueError,
                                'type parameter must be either pull or push',
                                recipe.add_slave, entry=entry, known_hosts_file={})

    def test_install(self):
        recipe = self.new_recipe()

        promises_directory = tempfile.mkdtemp()
        wrappers_directory = tempfile.mkdtemp()
        directory = tempfile.mkdtemp()
        feeds_directory = tempfile.mkdtemp()
        run_directory = tempfile.mkdtemp()
        cron_directory = tempfile.mkdtemp()

        recipe.options.update({
            'promises-directory': promises_directory,
            'wrappers-directory': wrappers_directory,
            'sshclient-binary': 'TEST_SSH_CLIENT',
            'directory': directory,
            'notifier-binary': 'TEST_NOTIFIER',
            'feeds': feeds_directory,
            'notifier-url': 'http://url.to.notifier/',
            'run-directory': run_directory,
            'cron-entries': cron_directory,
            'known-hosts': 'TEST_KNOWN_HOSTS',
            'slave-instance-list': [
                {
                 "url": "http://url.to.pull/",
                 "type": "pull",
                 "notification-id": "pulltest",
                 "server-key": "TEST_SERVER_KEY",
                 "name": "TEST_NAME",
                 "notify": "http://url.to.notify/",
                 "frequency": "TEST_FREQUENCY"
                    }, {
                 "url": "http://url.to.push/",
                 "type": "push",
                 "notification-id": "pushtest",
                 "server-key": "TEST_SERVER_KEY",
                 "name": "TEST_NAME",
                 "notify": "http://url.to.notify/",
                 "frequency": "TEST_FREQUENCY"
                        }
                ]
            })

        recipe._install()

        six.assertCountEqual(self, os.listdir(promises_directory),
                              ['ssh-to-pulltest', 'ssh-to-pushtest'])

        six.assertCountEqual(self, os.listdir(wrappers_directory),
                              ['pulltest_raw', 'pulltest', 'pushtest_raw', 'pushtest'])

        six.assertCountEqual(self, os.listdir(directory),
                              ['TEST_NAME'])

        six.assertCountEqual(self, os.listdir(feeds_directory),
                              ['pulltest', 'pushtest'])

        six.assertCountEqual(self, os.listdir(run_directory),
                              [])

        six.assertCountEqual(self, os.listdir(cron_directory),
                              ['pulltest', 'pushtest'])

        shutil.rmtree(promises_directory)
        shutil.rmtree(wrappers_directory)
        shutil.rmtree(directory)
        shutil.rmtree(feeds_directory)
        shutil.rmtree(run_directory)
        shutil.rmtree(cron_directory)


