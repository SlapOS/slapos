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

import os
import requests
import re
from mimetypes import guess_type
from json.decoder import JSONDecodeError

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class TestPeerTube(SlapOSInstanceTestCase):
  def setUp(self):
    self.connection_parameters = self.computer_partition.getConnectionParameterDict()

  def test_get(self):
    url = self.connection_parameters['frontend-url']
    response = requests.get(url, verify=False)
    self.assertEqual(requests.codes['OK'], response.status_code)
    self.assertIn('PeerTube', response.text)
    response =requests.get(url + "/feeds/videos.xml?sort=-trending", verify=False)
    self.assertEqual(requests.codes['OK'], response.status_code)
    self.assertIn('rss', response.text)

  def test_video_upload(self):
    api_url = self.connection_parameters['frontend-url']
    # api_url: https://[2001:67c:1254:fd::9ee2]:9443
    # self.connection_parameters
    # {'backend-url': 'https://[2001:67c:1254:fd::9ee2]:9443', 'frontend-hostname': '[2001:67c:1254:fd::9ee2]:9443', 'frontend-url': 'https://[2001:67c:1254:fd::9ee2]:9443', 'password': '8ydTfRpv', 'username': 'root'}
    response = requests.get(api_url + '/api/v1/oauth-clients/local', verify=False)
    self.assertEqual(requests.codes['OK'], response.status_code)
    try:
      data = response.json()
    except JSONDecodeError:
      self.fail("No json file returned! Maybe your Peertube API is incorrect.")

    client_id = data['client_id']
    client_secret = data['client_secret']
    username = self.connection_parameters['username']
    password = self.connection_parameters['password']
    auth_data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'password',
        'response_type': 'code',
        'username': username,
        'password': password
    }

    auth_result = requests.post(api_url + '/api/v1/users/token', data=auth_data, verify=False)
    self.assertEqual(requests.codes['OK'], auth_result.status_code)
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
    file_path = "./small.mp4"
    file_mime_type = guess_type(file_path)[0]

    with open(file_path, 'rb') as f:
        video_data = {
            'channelId': 1,
            'name': video_name,
            'commentEnabled': False,
        }
        upload_response = requests.post(
            api_url + '/api/v1/videos/upload',
            headers=headers,
            data=video_data,
            files={'videofile': (os.path.basename(file_path), f, file_mime_type)},
            verify=False
        )
    try:
      video_ids = upload_response.json()
    except JSONDecodeError:
      self.fail("No json file returned! Maybe your Peertube API is incorrect.")
    # {'video': {'id': 7, 'shortUUID': 'nrnKJNCsRP7NkwRr51TK3e', 'uuid': 'ad9ae99d-07db-4e4c-adc3-73566d59a4c5'}}
    self.assertIn('video', video_ids)
    id = video_ids['video']['id']

    # Check the video is uploaded, we can get its stats
    response = requests.get(api_url + '/api/v1/videos/' + str(id) + '/stats/overall', headers=headers, verify=False)
    self.assertEqual(requests.codes['OK'], response.status_code)
    try:
      result = response.json()
    except JSONDecodeError:
      self.fail("No json file returned! Maybe your Peertube API is incorrect.")
    self.assertIn('totalWatchTime', response.json())

    # Check the transcoding is enabled
    response = requests.get(api_url + '/api/v1/config', headers=headers, verify=False)
    try:
      result = response.json()
    except JSONDecodeError:
      self.fail("No json file returned! Maybe your Peertube API is incorrect.")
    # {
    #   'hls': {'enabled': True},
    #   'webtorrent': {'enabled': False},
    #   'enabledResolutions': [144, 240, 360, 480, 720, 1080, 1440, 2160],
    #   'profile': 'default',
    #   'availableProfiles': ['default']
    # }
    self.assertIn("hls", result['transcoding'])
    self.assertIn("True", str(result['transcoding']['hls']))
