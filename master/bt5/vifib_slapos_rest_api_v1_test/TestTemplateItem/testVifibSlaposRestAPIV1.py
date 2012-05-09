from Products.ERP5Type.tests.ERP5TypeTestCase import ERP5TypeTestCase
from Products.ERP5Type.Base import WorkflowMethod
import transaction
import httplib
import urlparse
import json
import tempfile
import os
import xml_marshaller

class Simulator:
  def __init__(self, outfile):
    self.outfile = outfile

  def __call__(self, *args, **kwargs):
    """Simulation Method"""
    open(self.outfile, 'a').write('recargs = %r\nreckwargs = %r' % (args, kwargs))

class RaisingSimulator(Simulator):
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

class VifibSlaposRestAPIV1Mixin(ERP5TypeTestCase):
  def generateNewId(self):
    return str(self.getPortalObject().portal_ids.generateNewId(
                                     id_group=('slapos_rest_api_v1_test')))

  def createPerson(self):
    customer = self.cloneByPath('person_module/template_member')
    customer_reference = 'P' + self.generateNewId()
    customer.edit(
      reference=customer_reference,
      default_email_url_string=customer_reference+'@example.com')
    customer.validate()
    for assignment in customer.contentValues(portal_type='Assignment'):
      assignment.open()

    customer.requestSoftwareInstance = Simulator(self.person_request_simulator)

    transaction.commit()
    customer.recursiveImmediateReindexObject()
    transaction.commit()
    customer.updateLocalRolesOnSecurityGroups()
    transaction.commit()
    customer.recursiveImmediateReindexObject()
    return customer, customer_reference

  def afterSetUp(self):
    self.test_random_id = self.generateNewId()
    self.access_control_allow_headers = 'some, funny, headers, ' \
      'always, expected, %s' % self.test_random_id

    self.document_list = []
    self.portal = self.getPortalObject()

    self.api_url = self.portal.portal_vifib_rest_api_v1.absolute_url()
    self.api_scheme, self.api_netloc, self.api_path, self.api_query, \
      self.api_fragment = urlparse.urlsplit(self.api_url)

    self.connection = CustomHeaderHTTPConnection(host=self.api_netloc,
      custom_header={
        'Access-Control-Allow-Headers': self.access_control_allow_headers,
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      })

    self.person_request_simulator = tempfile.mkstemp()[1]
    self.customer, self.customer_reference = self.createPerson()
    transaction.commit()

  def beforeTearDown(self):
    if os.path.exists(self.person_request_simulator):
      os.unlink(self.person_request_simulator)

  def cloneByPath(self, path):
    return self.portal.restrictedTraverse(path).Base_createCloneDocument(
      batch_mode=1)

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

  def assertResponseNoContentType(self):
    self.assertEqual(self.response.getheader('Content-Type'), None)

  def assertPersonRequestSimulatorEmpty(self):
    self.assertEqual(open(self.person_request_simulator).read(), '')

  def assertPersonRequestSimulator(self, args, kwargs):
    # fillup magic
    recargs = ()
    reckwargs = {}
    exec(open(self.person_request_simulator).read())
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

class TestInstanceRequest(VifibSlaposRestAPIV1Mixin):
  def test_not_logged_in(self):
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance']))
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(401)
    self.assertTrue(self.response.getheader('Location') is not None)
    auth = self.response.getheader('WWW-Authenticate')
    self.assertTrue(auth is not None)
    self.assertTrue('Bearer realm="' in auth)
    self.assertPersonRequestSimulatorEmpty()

  def test_no_json(self):
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance']),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(400)
    self.assertResponseJson()
    self.assertEqual({'error': "Data is not json object."}, self.json_response)
    self.assertPersonRequestSimulatorEmpty()

  def test_bad_json(self):
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance']),
      body='This is not JSON',
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(400)
    self.assertResponseJson()
    self.assertEqual({'error': "Data is not json object."}, self.json_response)
    self.assertPersonRequestSimulatorEmpty()

  def test_empty_json(self):
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
    self.assertPersonRequestSimulatorEmpty()

  def test_status_slave_missing_json(self):
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
    self.assertPersonRequestSimulatorEmpty()

  def test_slave_not_bool(self):
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
    self.assertPersonRequestSimulatorEmpty()

  def test_correct(self):
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
    self.assertPersonRequestSimulator((), kwargs)
    self.assertEqual({
        "status": "processing",
        },
      self.json_response)

  def test_additional_key_json(self):
    kw_request = {
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
    kwargs = kw_request.copy()
    kwargs.update(**{'wrong_key': 'Be ignored'})
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance']),
      body=json.dumps(kwargs),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(202)
    self.assertResponseJson()
    self.assertPersonRequestSimulator((), kw_request)
    self.assertEqual({
        "status": "processing",
        },
      self.json_response)

  def test_correct_server_side_raise(self):
    self.customer.requestSoftwareInstance = \
      RaisingSimulator(AttributeError)
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
    self.assertPersonRequestSimulatorEmpty()

  def test_content_negotiation_headers(self):
    self.connection = CustomHeaderHTTPConnection(host=self.api_netloc,
      custom_header={
        'Access-Control-Allow-Headers': self.access_control_allow_headers
      })
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
    self.assertResponseCode(400)
    self.assertResponseJson()
    self.assertEqual({
      'Content-Type': "Header with value 'application/json' is required.",
      'Accept': "Header with value 'application/json' is required."},
      self.json_response)
    self.assertPersonRequestSimulatorEmpty()

    # now check with incorrect headers
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance']),
      body=json.dumps(kwargs),
      headers={'REMOTE_USER': self.customer_reference,
        'Content-Type': 'please/complain',
        'Accept': 'please/complain'})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(400)
    self.assertResponseJson()
    self.assertEqual({
      'Content-Type': "Header with value 'application/json' is required.",
      'Accept': "Header with value 'application/json' is required."},
      self.json_response)
    self.assertPersonRequestSimulatorEmpty()
    # and with correct ones are set by default

class TestInstanceOPTIONS(VifibSlaposRestAPIV1Mixin):
  def test_OPTIONS_not_logged_in(self):
    self.connection = CustomHeaderHTTPConnection(host=self.api_netloc,
      custom_header={
        'Access-Control-Allow-Headers': self.access_control_allow_headers
      })
    self.connection.request(method='OPTIONS',
      url='/'.join([self.api_path, 'instance']))
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(204)
    self.assertResponseNoContentType()
    self.assertPersonRequestSimulatorEmpty()

class VifibSlaposRestAPIV1InstanceMixin(VifibSlaposRestAPIV1Mixin):
  def afterSetUp(self):
    VifibSlaposRestAPIV1Mixin.afterSetUp(self)
    self.software_instance = self.createSoftwareInstance(self.customer)

  def createSoftwareInstance(self, person):
    software_instance = self.cloneByPath(
      'software_instance_module/template_software_instance')
    hosting_subscription = self.cloneByPath(
      'hosting_subscription_module/template_hosting_subscription')
    software_instance.edit(
      reference='SI' + self.test_random_id,
      ssl_key='SSL Key',
      ssl_certificate='SSL Certificate'
    )
    software_instance.validate()
    hosting_subscription.edit(
      reference='HS' + self.test_random_id,
      predecessor=software_instance.getRelativeUrl(),
      destination_section=person.getRelativeUrl()
    )
    hosting_subscription.validate()
    transaction.commit()
    hosting_subscription.updateLocalRolesOnSecurityGroups()
    transaction.commit()
    hosting_subscription.recursiveImmediateReindexObject()
    transaction.commit()
    software_instance.manage_setLocalRoles(person.getReference(),
      ['Assignee'])
    transaction.commit()
    software_instance.recursiveImmediateReindexObject()
    return software_instance

  # needed to avoid calling interaction and being able to destroy XML
  @WorkflowMethod.disable
  def _destroySoftwareInstanceTextContentXml(self, software_instance):
    software_instance.setTextContent('This is bad XML')
    transaction.commit()
    software_instance.recursiveImmediateReindexObject()

class TestInstanceGET(VifibSlaposRestAPIV1InstanceMixin):
  def test_non_existing(self):
    non_existing = 'software_instance_module/' + self.generateNewId()
    try:
      self.portal.restrictedTraverse(non_existing)
    except KeyError:
      pass
    else:
      raise AssertionError('It was impossible to test')
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance',
      non_existing]),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(404)

  def test_something_else(self):
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance',
      self.software_instance.getPredecessorRelatedValue().getRelativeUrl()]),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(404)

  def test_bad_xml(self):
    self._destroySoftwareInstanceTextContentXml(self.software_instance)
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance',
      self.software_instance.getRelativeUrl()]),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(500)
    self.assertResponseJson()
    self.assertEqual({
      "error": "There is system issue, please try again later."},
      self.json_response)

  def test(self):
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance',
      self.software_instance.getRelativeUrl()]),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(200)
    self.assertResponseJson()
    self.assertEqual({
      "status": "draft",
      "connection": {
        "parameter1": "valueof1",
        "parameter2": "https://niut:pass@example.com:4567/arfarf/oink?m=1#4.5"},
      "partition": {
        "public_ip": [],
        "tap_interface": "",
        "private_ip": []},
      "slave": False,
      "children_list": [],
      "title": "Template Software Instance",
      "software_type": "RootSoftwareInstance",
      "parameter": {
        "parameter1": "valueof1",
        "parameter2": "valueof2"},
      "software_release": "",
      "sla": {"computer_guid": "SOMECOMP"}},
      self.json_response)

  def test_other_one(self):
    person, person_reference = self.createPerson()
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance',
      self.software_instance.getRelativeUrl()]),
      headers={'REMOTE_USER': person_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(404)

class TestInstanceGETcertificate(VifibSlaposRestAPIV1InstanceMixin):
  def test(self):
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance',
        self.software_instance.getRelativeUrl(), 'certificate']),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(200)
    self.assertResponseJson()
    self.assertEqual({
      "ssl_key": "SSL Key",
      "ssl_certificate": "SSL Certificate"
      },
      self.json_response)

  def test_bad_xml(self):
    self._destroySoftwareInstanceTextContentXml(self.software_instance)
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance',
        self.software_instance.getRelativeUrl(), 'certificate']),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(200)
    self.assertResponseJson()
    self.assertEqual({
      "ssl_key": "SSL Key",
      "ssl_certificate": "SSL Certificate"
      },
      self.json_response)

  def test_non_existing(self):
    non_existing = 'software_instance_module/' + self.generateNewId()
    try:
      self.portal.restrictedTraverse(non_existing)
    except KeyError:
      pass
    else:
      raise AssertionError('It was impossible to test')
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance',
      non_existing, 'certificate']),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(404)

  def test_something_else(self):
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance',
      self.software_instance.getPredecessorRelatedValue().getRelativeUrl(),
      'certificate']),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(404)

  def test_other_one(self):
    person, person_reference = self.createPerson()
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance',
      self.software_instance.getRelativeUrl(), 'certificate']),
      headers={'REMOTE_USER': person_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(404)

class VifibSlaposRestAPIV1BangMixin(VifibSlaposRestAPIV1InstanceMixin):
  def afterSetUp(self):
    super(VifibSlaposRestAPIV1BangMixin, self).afterSetUp()
    self.instance_bang_simulator = tempfile.mkstemp()[1]
    self.software_instance.reportComputerPartitionBang = Simulator(
      self.instance_bang_simulator)
    transaction.commit()

  def beforeTearDown(self):
    super(VifibSlaposRestAPIV1BangMixin, self).beforeTearDown()
    if os.path.exists(self.instance_bang_simulator):
      os.unlink(self.instance_bang_simulator)

  def assertInstanceBangSimulatorEmpty(self):
    self.assertEqual(open(self.instance_bang_simulator).read(), '')

  def assertInstanceBangSimulator(self, args, kwargs):
    # fillup magic
    recargs = ()
    reckwargs = {}
    exec(open(self.instance_bang_simulator).read())
    # do the same translation magic as in workflow
    kwargs['comment'] = kwargs.pop('log')
    self.assertEqual(args, recargs)
    self.assertEqual(kwargs, reckwargs)

class TestInstancePOSTbang(VifibSlaposRestAPIV1BangMixin):
  def test(self):
    kwargs = {'log': 'This is cool log!'}
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance',
      self.software_instance.getRelativeUrl(), 'bang']),
      body=json.dumps(kwargs),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(204)
    self.assertInstanceBangSimulator((), kwargs)

  def test_bad_xml(self):
    self._destroySoftwareInstanceTextContentXml(self.software_instance)
    kwargs = {'log': 'This is cool log!'}
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance',
      self.software_instance.getRelativeUrl(), 'bang']),
      body=json.dumps(kwargs),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(204)
    self.assertInstanceBangSimulator((), kwargs)

  def test_non_existing(self):
    non_existing = 'software_instance_module/' + self.generateNewId()
    try:
      self.portal.restrictedTraverse(non_existing)
    except KeyError:
      pass
    else:
      raise AssertionError('It was impossible to test')
    kwargs = {'log': 'This is cool log!'}
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance',
      non_existing, 'bang']),
      body=json.dumps(kwargs),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(404)
    self.assertInstanceBangSimulatorEmpty()

  def test_something_else(self):
    kwargs = {'log': 'This is cool log!'}
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance',
      self.software_instance.getPredecessorRelatedValue().getRelativeUrl(),
      'bang']), body=json.dumps(kwargs),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(404)
    self.assertInstanceBangSimulatorEmpty()

  def test_other_one(self):
    kwargs = {'log': 'This is cool log!'}
    person, person_reference = self.createPerson()
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance',
      self.software_instance.getPredecessorRelatedValue().getRelativeUrl(),
      'bang']), body=json.dumps(kwargs),
      headers={'REMOTE_USER': person_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(404)
    self.assertInstanceBangSimulatorEmpty()

  def test_no_json(self):
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance',
      self.software_instance.getRelativeUrl(), 'bang']),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(400)
    self.assertResponseJson()
    self.assertEqual({'error': "Data is not json object."}, self.json_response)
    self.assertInstanceBangSimulatorEmpty()

  def test_bad_json(self):
    kwargs = {'wrong_key': 'This is cool log!'}
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance',
      self.software_instance.getPredecessorRelatedValue().getRelativeUrl(),
      'bang']), body=json.dumps(kwargs),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(400)
    self.assertResponseJson()
    self.assertEqual({'log': 'Missing.'}, self.json_response)
    self.assertInstanceBangSimulatorEmpty()

  def test_empty_json(self):
    kwargs = {}
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance',
      self.software_instance.getPredecessorRelatedValue().getRelativeUrl(),
      'bang']), body=json.dumps(kwargs),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(400)
    self.assertResponseJson()
    self.assertEqual({'log': 'Missing.'}, self.json_response)
    self.assertInstanceBangSimulatorEmpty()

  def test_additional_key_json(self):
    kw_log = {'log': 'This is cool log!'}
    kwargs = kw_log.copy()
    kwargs.update(**{'wrong_key': 'Be ignored'})
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance',
      self.software_instance.getRelativeUrl(),
      'bang']), body=json.dumps(kwargs),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(204)
    self.assertInstanceBangSimulator((), kw_log)

  def test_log_not_string(self):
    kwargs = {'log': True}
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance',
      self.software_instance.getPredecessorRelatedValue().getRelativeUrl(),
      'bang']), body=json.dumps(kwargs),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(400)
    self.assertResponseJson()
    self.assertEqual({'log': 'Not a string.'}, self.json_response)
    self.assertInstanceBangSimulatorEmpty()
