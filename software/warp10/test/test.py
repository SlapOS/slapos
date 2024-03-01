import os
import requests

from slapos.testing.testcase import makeModuleSetUpAndTestCaseClass

setUpModule, SlapOSInstanceTestCase = makeModuleSetUpAndTestCaseClass(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'software.cfg')))


class TestWarp10(SlapOSInstanceTestCase):

  def test_web(self):
    params = self.computer_partition.getConnectionParameterDict()

    # check that tokens are not empty ( like @tomo suggested - EDIT: I misunderstood, his idea was to check this in a promise )
    self.assertTrue(params['read-token'])

    response = requests.get(params['url'])
# # maybe tokens are needed here for authentication, then it could be something like that instead:
#     response = requests.get(url, headers={'read-token': params['read-token']})

    self.assertEqual(requests.codes['OK'], response.status_code)
    # self.assertIn("*** something expected in the HTML page ***", response.text)
