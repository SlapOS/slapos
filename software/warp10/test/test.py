import os
import requests

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class TestWarp10(SlapOSInstanceTestCase):

  def setUp(self):
    self.params = self.computer_partition.getConnectionParameterDict()


  ##
  ## Check that tokens are not empty
  ##
  def test_tokens_availability(self):
    self.assertTrue(self.params['read-token'])
    self.assertTrue(self.params['write-token'])
    self.assertTrue(self.params['sensision-read-token'])
    self.assertTrue(self.params['sensision-write-token'])

  ##
  ## Verify if check-url is ok
  ##
  def test_backend_url(self):
    response = requests.get(self.params['backend-url'] + "/api/v0/check")
    self.assertEqual(requests.codes['OK'], response.status_code)

  ##
  ## Test read/write/deletion with a set of read/write token
  ##
  def read_write_data(self, read_token, write_token):
    endpoint = self.params['backend-url'] + "/api/v0/exec"
    gts = 'slapos.test'
    value = 42

    # Write
    query = f"NEWGTS '{gts}' RENAME NOW NaN NaN NaN {value} ADDVALUE '{write_token}' UPDATE"
    response = requests.post(endpoint, data = query)
    self.assertEqual(requests.codes['OK'], response.status_code)

    # Read
    query = f"[ '{read_token}' '{gts}' {{}} MAXLONG MAXLONG ] FETCH 0 GET VALUES"
    response = requests.post(endpoint, data = query)
    self.assertEqual(requests.codes['OK'], response.status_code)
    self.assertEqual(f"[[{value}]]", response.text)

    # Delete
    query = f"'{write_token}' '{gts}{{}}' NULL NULL MAXLONG DELETE"
    print(query)
    response = requests.post(endpoint, data = query)
    self.assertEqual(requests.codes['OK'], response.status_code)

    # Confirm deletion
    query = f"[ '{read_token}' '{gts}' {{}} MAXLONG MAXLONG ] FETCH [] =="
    response = requests.post(endpoint, data = query)
    self.assertEqual(requests.codes['OK'], response.status_code)
    self.assertEqual(f"[true]", response.text)


  ##
  ## Test standard token
  ##
  def test_standard_token(self):
    self.read_write_data(self.params['read-token'], self.params['write-token'])

  ##
  ## Test sensision token
  ##
  def test_sensision_token(self):
    self.read_write_data(self.params['sensision-read-token'], self.params['sensision-write-token'])
