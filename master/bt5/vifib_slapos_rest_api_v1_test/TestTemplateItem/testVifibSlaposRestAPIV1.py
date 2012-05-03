from Products.ERP5Type.tests.ERP5TypeTestCase import ERP5TypeTestCase
import transaction
import httplib
import urlparse
import json
import tempfile
import os
import xml_marshaller

class Person_requestSoftwareInstanceSimulator:
  def __init__(self, outfile):
    self.outfile = outfile

  def __call__(self, *args, **kwargs):
    """Simulation Method"""
    open(self.outfile, 'a').write('recargs = %r\nreckwargs = %r' % (args, kwargs))

class Person_requestSoftwareInstanceRaisingSimulator(Person_requestSoftwareInstanceSimulator):
  def __init__(self, exception):
    self.exception = exception

  def __call__(self, *args, **kwargs):
    """Simulation Method"""
    raise self.exception

class CustomHeaderHTTPConnection(httplib.HTTPConnection):
  def __init__(self, custom_header, *args, **kwargs):
    self._custom_header = custom_header
    httplib.HTTPConnection.__init__(self, *args, **kwargs)

  def request(self, *args, **kwargs):
    headers = kwargs.get('headers', {})
    headers.update(self._custom_header)
    kwargs['headers'] = headers
    return httplib.HTTPConnection.request(self, *args, **kwargs)

class TestVifibSlaposRestAPIV1(ERP5TypeTestCase):
  def generateNewId(self):
    return str(self.getPortalObject().portal_ids.generateNewId(
                                     id_group=('slapos_rest_api_v1_test')))

  def reindexAndUpdateLocalRoles(self):
    # reindex and update roles for all, and reindex again to update catalog
    transaction.commit()
    for o in self.document_list:
      o.recursiveImmediateReindexObject()
      transaction.commit()
    for o in self.document_list:
      o.updateLocalRolesOnSecurityGroups()
      transaction.commit()
    for o in self.document_list:
      o.recursiveImmediateReindexObject()
      transaction.commit()

  def afterSetUp(self):
    self.test_random_id = self.generateNewId()
    self.access_control_allow_headers = 'some, funny, headers, ' \
      'always, expected, %s' % self.test_random_id

    self.document_list = []
    self.portal = self.getPortalObject()
    self.customer = self.cloneByPath('person_module/template_member')
    self.customer_reference = 'P' + self.test_random_id
    self.customer.edit(
      reference=self.customer_reference,
      default_email_url_string=self.customer_reference+'@example.com')
    self.customer.validate()
    for assignment in self.customer.contentValues(portal_type='Assignment'):
      assignment.open()

    self.api_url = self.portal.portal_vifib_rest_api_v1.absolute_url()
    self.api_scheme, self.api_netloc, self.api_path, self.api_query, \
      self.api_fragment = urlparse.urlsplit(self.api_url)

    self.connection = CustomHeaderHTTPConnection(host=self.api_netloc,
      custom_header={
        'Access-Control-Allow-Headers': self.access_control_allow_headers
      })
    self.reindexAndUpdateLocalRoles()
    self.simulator = tempfile.mkstemp()[1]
    self.customer.requestSoftwareInstance = Person_requestSoftwareInstanceSimulator(
      self.simulator)
    transaction.commit()

  def beforeTearDown(self):
    if os.path.exists(self.simulator):
      os.unlink(self.simulator)

  def cloneByPath(self, path):
    o = self.portal.restrictedTraverse(path).Base_createCloneDocument(
      batch_mode=1)
    self.document_list.append(o)
    return o

  def prepareResponse(self):
    self.response = self.connection.getresponse()
    self.response_data = self.response.read()

  def assertBasicResponse(self):
    self.assertEqual(self.response.getheader('access-control-allow-origin'),
      '*')
    self.assertEqual(self.response.getheader('access-control-allow-methods'),
      'DELETE, PUT, POST, GET, OPTIONS')
    self.assertEqual(self.response.getheader('access-control-allow-headers'),
      self.access_control_allow_headers)

  def assertResponseCode(self, code):
    self.assertEqual(self.response.status, code,
      '%s was expected, but got %s with response:\n%s' %
        (code, self.response.status, self.response_data))

  def assertResponseJson(self):
    self.assertEqual(self.response.getheader('Content-Type'), 'application/json')
    self.json_response = json.loads(self.response_data)

  def assertSimulatorEmpty(self):
    self.assertEqual(open(self.simulator).read(), '')

  def assertSimulator(self, args, kwargs):
    # fillup magic
    recargs = ()
    reckwargs = {}
    exec(open(self.simulator).read())
    # do the same translation magic as in tool
    kwargs = kwargs.copy()
    for k_j, k_i in (
        ('software_release', 'software_release'),
        ('title', 'software_title'),
        ('software_type', 'software_type'),
        ('parameter', 'instance_xml'),
        ('sla', 'sla_xml'),
        ('slave', 'shared'),
        ('status', 'state')
      ):
      if k_j in ('sla', 'parameter'):
        reckwargs[k_i] = xml_marshaller.xml_marshaller.loads(reckwargs.pop(k_i))
      kwargs[k_i] = kwargs.pop(k_j)
    self.assertEqual(args, recargs)
    self.assertEqual(kwargs, reckwargs)
    
  def test_request_not_logged_in(self):
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance']))
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(401)
    self.assertTrue(self.response.getheader('Location') is not None)
    auth = self.response.getheader('WWW-Authenticate')
    self.assertTrue(auth is not None)
    self.assertTrue('Bearer realm="' in auth)
    self.assertSimulatorEmpty()

  def test_request_no_json(self):
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance']),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(400)
    self.assertResponseJson()
    self.assertTrue('error' in self.json_response)
    self.assertEqual("Data is not json object.", self.json_response['error'])
    self.assertSimulatorEmpty()

  def test_request_bad_json(self):
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance']),
      body='This is not JSON',
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(400)
    self.assertResponseJson()
    self.assertTrue('error' in self.json_response)
    self.assertEqual("Data is not json object.", self.json_response['error'])
    self.assertSimulatorEmpty()

  def test_request_empty_json(self):
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance']),
      body='{}',
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(400)
    self.assertResponseJson()
    self.assertEqual({
        "status": "Missing.",
        "slave": "Missing.",
        "title": "Missing.",
        "software_release": "Missing.",
        "software_type": "Missing.",
        "parameter": "Missing.",
        "sla": "Missing."},
      self.json_response)
    self.assertSimulatorEmpty()

  def test_request_status_slave_missing_json(self):
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance']),
      body="""
{
  "title": "My unique instance", 
  "software_release": "http://example.com/example.cfg", 
  "software_type": "type_provided_by_the_software", 
  "parameter": {
    "Custom1": "one string", 
    "Custom2": "one float", 
    "Custom3": [
      "abc", 
      "def"
    ]
  }, 
  "sla": {
    "computer_id": "COMP-0"
  }
}""",
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(400)
    self.assertResponseJson()
    self.assertEqual({
        "status": "Missing.",
        "slave": "Missing."
        },
      self.json_response)
    self.assertSimulatorEmpty()

  def test_request_slave_not_bool(self):
    kwargs = {
      'parameter': {
        'Custom1': 'one string',
        'Custom2': 'one float',
        'Custom3': ['abc', 'def']},
      'title': 'My unique instance',
      'software_release': 'http://example.com/example.cfg',
      'status': 'started',
      'sla': {
        'computer_id': 'COMP-0'},
      'software_type': 'type_provided_by_the_software',
      'slave': "True"}
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance']),
      body=json.dumps(kwargs),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(400)
    self.assertResponseJson()
    self.assertEqual({
        "slave": "Not boolean.",
        },
      self.json_response)
    self.assertSimulatorEmpty()

  def test_request_correct(self):
    kwargs = {
      'parameter': {
        'Custom1': 'one string',
        'Custom2': 'one float',
        'Custom3': ['abc', 'def']},
      'title': 'My unique instance',
      'software_release': 'http://example.com/example.cfg',
      'status': 'started',
      'sla': {
        'computer_id': 'COMP-0'},
      'software_type': 'type_provided_by_the_software',
      'slave': True}
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance']),
      body=json.dumps(kwargs),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(202)
    self.assertResponseJson()
    self.assertSimulator((), kwargs)
    self.assertEqual({
        "status": "processing",
        },
      self.json_response)

  def test_request_correct_server_side_raise(self):
    self.customer.requestSoftwareInstance = \
      Person_requestSoftwareInstanceRaisingSimulator(AttributeError)
    transaction.commit()
    kwargs = {
      'parameter': {
        'Custom1': 'one string',
        'Custom2': 'one float',
        'Custom3': ['abc', 'def']},
      'title': 'My unique instance',
      'software_release': 'http://example.com/example.cfg',
      'status': 'started',
      'sla': {
        'computer_id': 'COMP-0'},
      'software_type': 'type_provided_by_the_software',
      'slave': True}
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance']),
      body=json.dumps(kwargs),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(500)
    self.assertResponseJson()
    self.assertEqual({
        "error": "There is system issue, please try again later.",
        },
      self.json_response)
    self.assertSimulatorEmpty()

  def test_OPTIONS(self):
    raise NotImplementedError
