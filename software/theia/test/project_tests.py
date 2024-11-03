##############################################################################
#
# Copyright (c) 2019 Nexedi SA and Contributors. All Rights Reserved.
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

import gzip
import json
import os
import re
import subprocess
import time
import shutil
import requests
import tempfile

from datetime import datetime, timedelta
from urllib.parse import urljoin
from mimetypes import guess_type
from json.decoder import JSONDecodeError

from slapos.testing.testcase import installSoftwareUrlList

import test_resiliency
from test import SlapOSInstanceTestCase, theia_software_release_url


erp5_software_release_url = os.path.abspath(
  os.path.join(
    os.path.dirname(__file__), '..', '..', 'erp5', 'software.cfg'))
peertube_software_release_url = os.path.abspath(
  os.path.join(
    os.path.dirname(__file__), '..', '..', 'peertube', 'software.cfg'))
gitlab_software_release_url = os.path.abspath(
  os.path.join(
    os.path.dirname(__file__), '..', '..', 'gitlab', 'software.cfg'))


def setUpModule():
  installSoftwareUrlList(
    SlapOSInstanceTestCase,
    [theia_software_release_url, erp5_software_release_url],
    debug=bool(int(os.environ.get('SLAPOS_TEST_DEBUG', 0))),
  )


class ERP5Mixin(object):
  _test_software_url = erp5_software_release_url
  _connexion_parameters_regex = re.compile(r"{.*}", re.DOTALL)

  def _getERP5ConnexionParameters(self, instance_type='export'):
    out = self.captureSlapos(
      'request', 'test_instance', self._test_software_url,
      stderr=subprocess.STDOUT,
      text=True,
    )
    print(out)
    return json.loads(self._connexion_parameters_regex.search(out).group(0).replace("'", '"'))

  def _getERP5Url(self, connexion_parameters, path=''):
    return urljoin(connexion_parameters['family-default-v6'], path)

  def _getERP5User(self, connexion_parameters):
    return connexion_parameters['inituser-login']

  def _getERP5Password(self, connexion_parameters):
    return connexion_parameters['inituser-password']

  def _waitERP5connected(self, url, user, password):
    for _ in range(5):
      try:
        resp = requests.get('%s/getId' % url, auth=(user, password), verify=False, allow_redirects=False)
      except Exception:
        time.sleep(20)
        continue
      if resp.status_code != 200:
        time.sleep(20)
        continue
      break
    else:
      self.fail('Failed to connect to ERP5')
    self.assertEqual(resp.text, 'erp5')

  def _getERP5Partition(self, servicename):
    p = subprocess.Popen(
      (self._getSlapos(), 'node', 'status'),
      stdout=subprocess.PIPE, universal_newlines=True)
    out, _ = p.communicate()
    found = set()
    for line in out.splitlines():
      if servicename in line:
        found.add(line.split(':')[0])
    if not found:
      raise Exception("ERP5 %s partition not found" % servicename)
    elif len(found) > 1:
      raise Exception("Found several partitions for ERP5 %s" % servicename)
    return found.pop()

  def _getERP5PartitionPath(self, instance_type, servicename, *paths):
    partition = self._getERP5Partition(servicename)
    return self.getPartitionPath(
      instance_type, 'srv', 'runner', 'instance', partition, *paths)


class TestTheiaResilienceERP5(ERP5Mixin, test_resiliency.TestTheiaResilience):
  test_instance_max_retries = 12
  backup_max_tries = 480
  backup_wait_interval = 60

  def test_twice(self):
    # do nothing
    pass

  def _prepareExport(self):
    super(TestTheiaResilienceERP5, self)._prepareExport()

    # Connect to erp5
    info = self._getERP5ConnexionParameters()
    user = self._getERP5User(info)
    password = self._getERP5Password(info)
    url = self._getERP5Url(info, 'erp5')
    self._waitERP5connected(url, user, password)

    # Change title
    new_title = time.strftime("HelloTitle %a %d %b %Y %H:%M:%S", time.localtime(time.time()))
    requests.get('%s/portal_types/setTitle?value=%s' % (url, new_title), auth=(user, password), verify=False)
    resp = requests.get('%s/portal_types/getTitle' % url, auth=(user, password), verify=False, allow_redirects=False)
    self.assertEqual(resp.text, new_title)
    self._erp5_new_title = new_title

    # Wait until changes have been catalogued
    mariadb_partition = self._getERP5PartitionPath('export', 'mariadb')
    mysql_bin = os.path.join(mariadb_partition, 'bin', 'mysql')
    wait_activities_script = os.path.join(
      mariadb_partition, 'software_release', 'parts', 'erp5',
      'Products', 'CMFActivity', 'bin', 'wait_activities')
    subprocess.check_call((wait_activities_script, 'erp5'), env={'MYSQL': mysql_bin})

    # Check that changes have been catalogued
    output = subprocess.check_output(
      (mysql_bin, 'erp5', '-e', 'SELECT title FROM catalog WHERE id="portal_types"'),
      universal_newlines=True)
    self.assertIn(new_title, output)

    # Compute backup date in the near future
    soon = (datetime.now() + timedelta(minutes=4)).replace(second=0)
    date = '*:%d:00' % soon.minute
    params = '_={"zodb-zeo": {"backup-periodicity": "%s"}, "mariadb": {"backup-periodicity": "%s"} }' % (date, date)

    # Update ERP5 parameters
    print('Requesting ERP5 with parameters %s' % params)
    self.checkSlapos('request', 'test_instance', self._test_software_url, '--parameters', params)

    # Process twice to propagate parameter changes
    for _ in range(2):
      self.checkSlapos('node', 'instance')

    # Restart cron (actually all) services to let them take the new date into account
    # XXX this should not be required, updating ERP5 parameters should be enough
    self.callSlapos('node', 'restart', 'all')

    # Wait until after the programmed backup date, and a bit more
    t = (soon - datetime.now()).total_seconds()
    self.assertLess(0, t)
    time.sleep(t + 120)

    # Check that mariadb backup has started
    mariadb_backup = os.path.join(mariadb_partition, 'srv', 'backup', 'mariadb-full')
    mariadb_backup_dump, = os.listdir(mariadb_backup)

    # Check that zodb backup has started
    zodb_backup = self._getERP5PartitionPath('export', 'zeo', 'srv', 'backup', 'zodb', 'root')
    self.assertEqual(len(os.listdir(zodb_backup)), 3)

    # Check that mariadb catalog backup contains expected changes
    with gzip.open(os.path.join(mariadb_backup, mariadb_backup_dump)) as f:
      msg = "Mariadb catalog backup %s is not up to date" % mariadb_backup_dump
      self.assertIn(new_title.encode(), f.read(), msg)

  def _checkTakeover(self):
    super(TestTheiaResilienceERP5, self)._checkTakeover()

    # Connect to erp5
    info = self._getERP5ConnexionParameters()
    user = self._getERP5User(info)
    password = self._getERP5Password(info)
    url = self._getERP5Url(info, 'erp5')
    self._waitERP5connected(url, user, password)

    resp = requests.get('%s/portal_types/getTitle' % url, auth=(user, password), verify=False, allow_redirects=False)
    self.assertEqual(resp.text, self._erp5_new_title)

    # Check that the mariadb catalog is not yet restored
    mariadb_partition = self._getERP5PartitionPath('export', 'mariadb')
    mysql_bin = os.path.join(mariadb_partition, 'bin', 'mysql')
    query = 'SELECT title FROM catalog WHERE id="portal_types"'
    try:
      out = subprocess.check_output((mysql_bin, 'erp5', '-e', query), universal_newlines=True)
    except subprocess.CalledProcessError:
      out = ''
    self.assertNotIn(self._erp5_new_title, out)

    # Stop all services
    print("Stop all services")
    self.callSlapos('node', 'stop', 'all')

    # Manually restore mariadb from backup
    mariadb_restore_script = os.path.join(mariadb_partition, 'bin', 'restore-from-backup')
    print("Restore mariadb from backup")
    subprocess.check_call(mariadb_restore_script)

    # Check that the test instance is properly redeployed after restoring mariadb
    # This restarts the services and checks the promises of the test instance
    # Process twice to propagate state change
    for _ in range(2):
      self._processEmbeddedInstance(self.test_instance_max_retries)

    # Check that the mariadb catalog was properly restored
    out = subprocess.check_output((mysql_bin, 'erp5', '-e', query), universal_newlines=True)
    self.assertIn(self._erp5_new_title, out, 'Mariadb catalog is not properly restored')

class TestTheiaResiliencePeertube(test_resiliency.TestTheiaResilience):
  test_instance_max_retries = 12
  backup_max_tries = 480
  backup_wait_interval = 60
  _connexion_parameters_regex = re.compile(r"{.*}", re.DOTALL)
  _test_software_url = peertube_software_release_url

  def _getPeertubeConnexionParameters(self, instance_type='export'):
    out = self.captureSlapos(
      'request', 'test_instance', self._test_software_url,
      stderr=subprocess.STDOUT,
      text=True,
    )
    print(out)
    return json.loads(self._connexion_parameters_regex.search(out).group(0).replace("'", '"'))

  def test_twice(self):
    # do nothing
    pass

  def _prepareExport(self):
    super(TestTheiaResiliencePeertube, self)._prepareExport()

    postgresql_partition = self._getPeertubePartitionPath('export', 'postgres')
    postgresql_bin = os.path.join(postgresql_partition, 'bin', 'psql')
    postgres_bin = os.path.join(postgresql_partition, 'bin', 'postgres')
    postgresql_srv = os.path.join(postgresql_partition, 'srv', 'postgresql')

    peertube_conenction_info = self._getPeertubeConnexionParameters()
    frontend_url = peertube_conenction_info['frontend-url']

    response = requests.get(frontend_url + '/api/v1/oauth-clients/local', verify=False)
    self.assertEqual(requests.codes['OK'], response.status_code)
    try:
      data = response.json()
    except JSONDecodeError:
      self.fail("No json file returned! Maybe your Peertube API is incorrect.")

    client_id = data['client_id']
    client_secret = data['client_secret']
    username = peertube_conenction_info['username']
    password = peertube_conenction_info['password']
    auth_data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'password',
        'response_type': 'code',
        'username': username,
        'password': password
    }

    auth_result = requests.post(frontend_url + '/api/v1/users/token', data=auth_data, verify=False)
    try:
      auth_result_json = auth_result.json()
    except JSONDecodeError:
      self.fail("No json file returned! Maybe your Peertube API is incorrect.")

    token_type = auth_result_json['token_type']
    access_token = auth_result_json['access_token']
    headers = {
        'Authorization': token_type + ' ' + access_token
    }
    video_name = "Small test video"
    file_path = "../../peertube/test/small.mp4"
    pwd_file_path = os.path.realpath(__file__)
    print(pwd_file_path)
    file_mime_type = guess_type(file_path)[0]

    with open(file_path, 'rb') as f:
        video_data = {
            'channelId': 1,
            'name': video_name,
            'commentEnabled': False,
            'privacy': 1,
        }
        upload_response = requests.post(
            frontend_url + '/api/v1/videos/upload',
            headers=headers,
            data=video_data,
            files={'videofile': (os.path.basename(file_path), f, file_mime_type)},
            verify=False
        )
    try:
      video_ids = upload_response.json()
    except JSONDecodeError:
      self.fail("No json file returned! Maybe your Peertube API is incorrect.")
    # e.g: {'video': {'id': 7, 'shortUUID': 'nrnKJNCsRP7NkwRr51TK3e', 'uuid': 'ad9ae99d-07db-4e4c-adc3-73566d59a4c5'}}
    self.assertIn('video', video_ids)

    # Checked the modification has been updated in the database
    output = subprocess.check_output(
      (postgresql_bin, '-h', postgresql_srv, '-U', 'peertube', '-d', 'peertube_prod',
      '-c', 'SELECT * FROM "video"'),
      universal_newlines=True)
    self.assertIn("Small test video", output)

    # Do a fake periodically update
    # Compute backup date in the near future
    soon = (datetime.now() + timedelta(minutes=4)).replace(second=0)
    frequency = "%d * * * *" % soon.minute
    params = 'frequency=%s' % frequency

    # Update Peertube parameters
    print('Requesting Peertube with parameters %s' % params)
    self.checkSlapos('request', 'test_instance', self._test_software_url, '--parameters', params)

    self.checkSlapos('node', 'instance')

    self.callSlapos('node', 'restart', 'all')

    # Wait until after the programmed backup date, and a bit more
    t = (soon - datetime.now()).total_seconds()
    self.assertLess(0, t)
    time.sleep(t + 120)
    self.callSlapos('node', 'status')

    # Check that postgresql backup has started
    postgresql_backup = os.path.join(postgresql_partition, 'srv', 'backup')
    self.assertIn('peertube_prod-dump.db', os.listdir(postgresql_backup))

  def _checkTakeover(self):
    super(TestTheiaResiliencePeertube, self)._checkTakeover()

    postgresql_partition = self._getPeertubePartitionPath('export', 'postgres')
    postgresql_bin = os.path.join(postgresql_partition, 'bin', 'psql')
    postgres_bin = os.path.join(postgresql_partition, 'bin', 'postgres')
    postgresql_srv = os.path.join(postgresql_partition, 'srv', 'postgresql')

    peertube_conenction_info = self._getPeertubeConnexionParameters()
    frontend_url = peertube_conenction_info['frontend-url']
    storage_path = os.path.join(postgresql_partition, 'var', 'www', 'peertube', 'storage')

    # Wait for connect Peertube
    for _ in range(5):
      try:
        response = requests.get(frontend_url, verify=False, allow_redirects=False)
      except Exception:
        time.sleep(20)
        continue
      if response.status_code != 200:
        time.sleep(20)
        continue
      break
    else:
      self.fail('Failed to connect to Peertube')

    # Get the video path, the part of this path will be used in the video URL
    # e.g: var/www/peertube/storage/streaming-playlists/hls/XXXX/YYYY.mp4

    # path before hls dir
    hls_path = os.path.join(storage_path, 'streaming-playlists', 'hls')

    #Choose only one video path
    video_path = None
    for root, dirs, files in os.walk(hls_path):
      for a_file in files:
        if a_file.endswith('.mp4'):
          video_path = os.path.join(root, a_file)
          break
      else:
        continue
      break

    # path like "streaming-playlists/hls/XXXX/YYYY.mp4"
    self.assertIn('streaming-playlists', video_path)

    streaming_video_path = video_path[video_path.index('streaming-playlists'):]
    video_url = frontend_url + '/static/' + streaming_video_path
    response = requests.get(video_url, verify=False)
    # The video mp4 file is accesible through the URL
    self.assertEqual(requests.codes['OK'], response.status_code)

    video_feeds_url = frontend_url + '/feeds/videos.json'
    response = requests.get(video_feeds_url, verify=False)

    # The video feeds returns the correct status code
    self.assertEqual(requests.codes['OK'], response.status_code)
    try:
      video_data= response.json()
    except JSONDecodeError:
      self.fail("No json file returned! Maybe your Peertube feeds URL is incorrect.")

    # Check the first video title is in the response content
    video_title = video_data['items'][0]['title']
    self.assertIn("Small test video", video_title)

  def _getPeertubePartition(self, servicename):
    p = subprocess.Popen(
      (self._getSlapos(), 'node', 'status'),
      stdout=subprocess.PIPE, universal_newlines=True)
    out, _ = p.communicate()
    found = set()
    for line in out.splitlines():
      if servicename in line:
        found.add(line.split(':')[0])
    if not found:
      raise Exception("Peertube %s partition not found" % servicename)
    elif len(found) > 1:
      raise Exception("Found several partitions for Peertube %s" % servicename)
    return found.pop()

  def _getPeertubePartitionPath(self, instance_type, servicename, *paths):
    partition = self._getPeertubePartition(servicename)
    return self.getPartitionPath(
      instance_type, 'srv', 'runner', 'instance', partition, *paths)


class TestTheiaResilienceGitlab(test_resiliency.TestTheiaResilience):
  test_instance_max_retries = 50  # puma takes time to be ready
  backup_max_tries = 480
  backup_wait_interval = 60
  _connection_parameters_regex = re.compile(r"{.*}", re.DOTALL)
  _test_software_url = gitlab_software_release_url

  def setUp(self):
    self.temp_dir = os.path.realpath(tempfile.mkdtemp())
    self.temp_clone_dir = os.path.realpath(tempfile.mkdtemp())
    self.addCleanup(shutil.rmtree, self.temp_dir)
    self.addCleanup(shutil.rmtree, self.temp_clone_dir)

  def _getGitlabConnectionParameters(self, instance_type='export'):
    out = self.captureSlapos(
      'request', 'test_instance', self._test_software_url,
      stderr=subprocess.STDOUT,
      text=True,
    )
    self.logger.info("_getGitlabConnectionParameters output: %s", out)
    return json.loads(self._connection_parameters_regex.search(out).group(0).replace("'", '"'))

  def test_twice(self):
    # do nothing
    pass

  def _prepareExport(self):
    super(TestTheiaResilienceGitlab, self)._prepareExport()

    gitlab_partition = self._getGitlabPartitionPath('export', 'gitlab')
    gitlab_rails_bin = os.path.join(gitlab_partition, 'bin', 'gitlab-rails')
    os.chdir(self.temp_dir)

    # Get Gitlab parameters
    parameter_dict = self._getGitlabConnectionParameters()
    backend_url = parameter_dict['backend_url']

    print('Trying to connect to gitlab backend URL...')
    response = requests.get(backend_url, verify=False)
    self.assertEqual(requests.codes['OK'], response.status_code)

    # Set the password and token
    output = subprocess.check_output(
      (gitlab_rails_bin, 'runner', "user = User.find(1); user.password = 'nexedi4321'; user.password_confirmation = 'nexedi4321'; user.save!"),
      universal_newlines=True)
    output = subprocess.check_output(
      (gitlab_rails_bin, 'runner', "user = User.find(1); token = user.personal_access_tokens.create(scopes: [:api], name: 'Root token'); token.set_token('SLurtnxPscPsU-SDm4oN'); token.save!"),
      universal_newlines=True)

    # Create a new project
    print("Gitlab create a project")
    path = '/api/v4/projects'
    parameter_dict = {'name': 'sample-test', 'namespace': 'open'}
    # Token can be set manually
    headers = {"PRIVATE-TOKEN" : 'SLurtnxPscPsU-SDm4oN'}
    response = requests.post(backend_url + path, params=parameter_dict,
                                  headers=headers, verify=False)

    # Check the project is exist
    print("Gitlab check project is exist")
    path = '/api/v4/projects'
    response = requests.get(backend_url + path, params={'search': 'sample-test'}, headers=headers, verify=False)
    try:
      projects = response.json()
    except JSONDecodeError:
      self.fail("No json file returned! Maybe your Gitlab URL is incorrect.")

    # Only one project matches the search
    self.assertEqual(len(projects), 1)
    # The project name is sample-test, which we created above.
    self.assertIn("sample-test", projects[0]['name_with_namespace'])

    # Get repo url, default one is https://lab.example.com/root/sample-test.git
    # We need the path like https://[2001:67c:1254:e:c4::5041]:7777/root/sample-test
    project_1 = projects[0]
    repo_url = backend_url.replace("https://", "") + "/" + project_1['path_with_namespace']
    # Clone the repo with token
    clone_url = 'https://oauth2:' + 'SLurtnxPscPsU-SDm4oN@' + repo_url
    repo_path = os.path.join(os.getcwd(), project_1['name'])
    print(repo_path)
    if os.path.exists(repo_path):
      shutil.rmtree(repo_path, ignore_errors=True)
    output = subprocess.check_output(('git', 'clone', '-c', 'http.sslVerify=false', clone_url), universal_newlines=True)

    # Create a new file and push the commit
    f = open(os.path.join(repo_path, 'file.txt'), 'x')
    f.write('This is the new file.')
    f.close()
    output = subprocess.check_output(('git', 'add', '.'), cwd=repo_path, universal_newlines=True)
    output = subprocess.check_output(('git', 'config', '--global', 'user.name', 'Resilience Test'), cwd=repo_path, universal_newlines=True)
    output = subprocess.check_output(('git', 'config', '--global', 'user.email', 'resilience-test@example.com'), cwd=repo_path, universal_newlines=True)
    output = subprocess.check_output(('git', 'commit', '-m', 'Initial commit'), cwd=repo_path, universal_newlines=True)
    output = subprocess.check_output(('git', 'push', 'origin'), cwd=repo_path, universal_newlines=True)

    # Do a fake periodically update
    # Compute backup date in the future
    # During slapos node instance, the static assets are recompiled, which takes a lot
    # of time, so we give it at least 20 minutes.
    soon = (datetime.now() + timedelta(minutes=20))
    frequency = "%d * * * *" % soon.minute
    params = 'backup_frequency=%s' % frequency

    # Update Gitlab parameters
    print('Requesting Gitlab with parameters %s' % params)
    self.checkSlapos('request', 'test_instance', self._test_software_url, '--parameters', params)

    self.checkSlapos('node', 'instance')

    self.callSlapos('node', 'restart', 'all')

    # Wait until after the programmed backup date, and a bit more
    t = ((soon - datetime.now()) + timedelta(minutes=10)).total_seconds()
    time.sleep(t)
    self.callSlapos('node', 'status')

    os.chdir(self.temp_clone_dir)
    repo_path = os.path.join(os.getcwd(), project_1['name'])
    print(repo_path)
    if os.path.exists(repo_path):
      shutil.rmtree(repo_path, ignore_errors=True)
    output = subprocess.check_output(('git', 'clone', '-c', 'http.sslVerify=false', clone_url), universal_newlines=True)

    # Check the file we committed in exist and the content is matching.
    output = subprocess.check_output(('git', 'show', 'origin/master:file.txt'), cwd=repo_path, universal_newlines=True)
    self.assertIn('This is the new file.', output)

  def _checkTakeover(self):
    super(TestTheiaResilienceGitlab, self)._checkTakeover()
    # Get Gitlab parameters
    parameter_dict = self._getGitlabConnectionParameters()
    backend_url = parameter_dict['backend_url']

    # The temp dir which created in theia0, it should be exist and contains the repo
    os.chdir(self.temp_dir)

    # Check the project is exist
    print("Gitlab check project is exist")
    path = '/api/v4/projects'
    headers = {"PRIVATE-TOKEN" : 'SLurtnxPscPsU-SDm4oN'}
    response = requests.get(backend_url + path, params={'search': 'sample-test'}, headers=headers, verify=False)
    try:
      projects = response.json()
    except JSONDecodeError:
      self.fail("No json file returned! Maybe your Gitlab URL is incorrect.")

    # Only one project exist
    self.assertEqual(len(projects), 1)
    # The project name is sample-test, which we created above.
    self.assertIn("sample-test", projects[0]['name_with_namespace'])
    project_1 = projects[0]
    repo_url = backend_url.replace("https://", "") + "/" + project_1['path_with_namespace']
    clone_url = 'https://oauth2:' + 'SLurtnxPscPsU-SDm4oN@' + repo_url
    repo_path = os.path.join(os.getcwd(), project_1['name'])

    # Check the file we committed in the original theia is exist and the content is matching.
    output = subprocess.check_output(('git', 'show', 'origin/master:file.txt'), cwd=repo_path, universal_newlines=True)
    self.assertIn('This is the new file.', output)


  def _getGitlabPartition(self, servicename):
    p = subprocess.Popen(
      (self._getSlapos(), 'node', 'status'),
      stdout=subprocess.PIPE, universal_newlines=True)
    out, _ = p.communicate()
    found = set()
    for line in out.splitlines():
      if servicename in line:
        found.add(line.split(':')[0])
    if not found:
      raise Exception("Gitlab %s partition not found" % servicename)
    elif len(found) > 1:
      raise Exception("Found several partitions for Gitlab %s" % servicename)
    return found.pop()

  def _getGitlabPartitionPath(self, instance_type, servicename, *paths):
    partition = self._getGitlabPartition(servicename)
    return self.getPartitionPath(
      instance_type, 'srv', 'runner', 'instance', partition, *paths)
