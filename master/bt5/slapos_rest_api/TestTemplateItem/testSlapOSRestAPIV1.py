# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
from Products.ERP5Type.Base import WorkflowMethod
import transaction
import httplib
import urllib
import urlparse
import json
import tempfile
import os
from App.Common import rfc1123_date
from DateTime import DateTime
import time

from Products.ERP5Type.tests.backportUnittest import skip

def _getMemcachedDict(self):
  return self.getPortal().portal_memcached.getMemcachedDict(
    key_prefix='slap_tool',
    plugin_path='portal_memcached/default_memcached_plugin')

def _logAccess(self, user_reference, context_reference, text):
  memcached_dict = self._getMemcachedDict()
  value = json.dumps({
    'user': '%s' % user_reference,
    'created_at': '%s' % rfc1123_date(DateTime()),
    'text': '%s' % text,
  })
  memcached_dict[context_reference] = value

class Simulator:
  def __init__(self, outfile, method):
    self.outfile = outfile
    self.method = method

  def __call__(self, *args, **kwargs):
    """Simulation Method"""
    old = open(self.outfile, 'r').read()
    if old:
      l = eval(old)
    else:
      l = []
    l.append({'recmethod': self.method,
      'recargs': args,
      'reckwargs': kwargs})
    open(self.outfile, 'w').write(repr(l))

class RaisingSimulator:
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

def SlapOSRestAPIV1MixinBase_afterSetUp(self):
  self.test_random_id = self.generateNewId()
  self.access_control_allow_headers = 'some, funny, headers, ' \
    'always, expected, %s' % self.test_random_id

  self.document_list = []
  self.portal = self.getPortalObject()

  self.api_url = self.portal.portal_slapos_rest_api.v1.getAPIRoot()
  self.api_scheme, self.api_netloc, self.api_path, self.api_query, \
    self.api_fragment = urlparse.urlsplit(self.api_url)

  self.connection = CustomHeaderHTTPConnection(host=self.api_netloc,
    custom_header={
      'Access-Control-Request-Headers': self.access_control_allow_headers,
      'Content-Type': 'application/json',
    })

class SlapOSRestAPIV1MixinBase(testSlapOSMixin):
  def generateNewId(self):
    return str(self.getPortalObject().portal_ids.generateNewId(
                                     id_group=('slapos_rest_api_v1_test')))

  def cloneByPath(self, path):
    return self.portal.restrictedTraverse(path).Base_createCloneDocument(
      batch_mode=1)

  def assertCacheControlHeader(self):
    self.assertEqual('must-revalidate',
      self.response.getheader('Cache-Control'))

  def _afterSetUp(self):
    super(SlapOSRestAPIV1MixinBase, self).afterSetUp()

  def afterSetUp(self):
    self._afterSetUp()
    SlapOSRestAPIV1MixinBase_afterSetUp(self)

  def beforeTearDown(self):
    pass

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

def SlapOSRestAPIV1Mixin_afterSetUp(self):
  SlapOSRestAPIV1MixinBase_afterSetUp(self)

  self.person_request_simulator = tempfile.mkstemp()[1]
  self.customer, self.customer_reference = self.createPerson()
  self.customer.requestSoftwareInstance = Simulator(self.person_request_simulator,
    'requestSoftwareInstance')
  transaction.commit()

def SlapOSRestAPIV1Mixin_beforeTearDown(self):
  if os.path.exists(self.person_request_simulator):
    os.unlink(self.person_request_simulator)

class SlapOSRestAPIV1Mixin(SlapOSRestAPIV1MixinBase):
  def createPerson(self):
    customer = self.cloneByPath('person_module/template_member')
    customer_reference = 'P' + self.generateNewId()
    customer.edit(
      reference=customer_reference,
      default_email_url_string=customer_reference+'@example.com')
    customer.validate()
    for assignment in customer.contentValues(portal_type='Assignment'):
      assignment.open()

    customer.manage_setLocalRoles(customer.getReference(),
      ['Associate'])
    transaction.commit()
    customer.recursiveImmediateReindexObject()
    transaction.commit()
    return customer, customer_reference

  def afterSetUp(self):
    self._afterSetUp()
    SlapOSRestAPIV1Mixin_afterSetUp(self)

  def beforeTearDown(self):
    SlapOSRestAPIV1Mixin_beforeTearDown(self)

  def assertPersonRequestSimulatorEmpty(self):
    self.assertEqual(open(self.person_request_simulator).read(), '')

  def assertPersonRequestSimulator(self, args, kwargs):
    stored = eval(open(self.person_request_simulator).read())
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
      kwargs[k_i] = kwargs.pop(k_j)
    self.assertEqual(stored,
      [{'recargs': args, 'reckwargs': kwargs,
      'recmethod': 'requestSoftwareInstance'}])
    reckwargs = stored[0]['reckwargs']
    self.assertEqual(
      set([
        type(reckwargs['software_title']), type(reckwargs['software_release']),
        type(reckwargs['software_type']), type(reckwargs['state']),
        type(reckwargs['instance_xml']), type(reckwargs['sla_xml'])
      ]),
      set([str])
    )

@skip('Undecided.')
class TestInstanceRequest(SlapOSRestAPIV1Mixin):
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
        "slave": "unicode is not bool.",
        },
      self.json_response)
    self.assertPersonRequestSimulatorEmpty()

  def test_incorrect_status(self):
    kwargs = {
      'parameter': {
        'Custom1': 'one string',
        'Custom2': 'one float',
        'Custom3': ['abc', 'def']},
      'title': 'My unique instance',
      'software_release': 'http://example.com/example.cfg',
      'status': 'badstatus',
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
        "status": "Status shall be one of: started, stopped, destroyed.",
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
    kwargs['parameter'] = '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n<i'\
      'nstance>\n  <parameter id="Custom1">one string</parameter>\n  <paramet'\
      'er id="Custom2">one float</parameter>\n  <parameter id="Custom3">[u\'a'\
      'bc\', u\'def\']</parameter>\n</instance>\n'
    kwargs['sla'] = '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n<instanc'\
      'e>\n  <parameter id="computer_id">COMP-0</parameter>\n</instance>\n'
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
    kw_request['parameter'] = '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n<i'\
      'nstance>\n  <parameter id="Custom1">one string</parameter>\n  <paramet'\
      'er id="Custom2">one float</parameter>\n  <parameter id="Custom3">[u\'a'\
      'bc\', u\'def\']</parameter>\n</instance>\n'
    kw_request['sla'] = '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n<instanc'\
      'e>\n  <parameter id="computer_id">COMP-0</parameter>\n</instance>\n'
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
        'Access-Control-Request-Headers': self.access_control_allow_headers
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
      'Content-Type': "Header with value '^application/json.*' is required."},
      self.json_response)
    self.assertPersonRequestSimulatorEmpty()

    # now check with incorrect headers
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance']),
      body=json.dumps(kwargs),
      headers={'REMOTE_USER': self.customer_reference,
        'Content-Type': 'please/complain',
        'Accept': 'be/silent'})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(400)
    self.assertResponseJson()
    self.assertEqual({
      'Content-Type': "Header with value '^application/json.*' is required."},
      self.json_response)
    self.assertPersonRequestSimulatorEmpty()
    # and with correct ones are set by default

@skip('Undecided.')
class TestInstanceOPTIONS(SlapOSRestAPIV1Mixin):
  def test_OPTIONS_not_logged_in(self):
    self.connection = CustomHeaderHTTPConnection(host=self.api_netloc,
      custom_header={
        'Access-Control-Request-Headers': self.access_control_allow_headers
      })
    self.connection.request(method='OPTIONS',
      url='/'.join([self.api_path, 'instance']))
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(204)
    self.assertResponseNoContentType()
    self.assertPersonRequestSimulatorEmpty()

def SlapOSRestAPIV1InstanceMixin_afterSetUp(self):
  SlapOSRestAPIV1Mixin_afterSetUp(self)
  self.software_instance = self.createSoftwareInstance(self.customer)

class SlapOSRestAPIV1InstanceMixin(SlapOSRestAPIV1Mixin):
  def afterSetUp(self):
    self._afterSetUp()
    SlapOSRestAPIV1InstanceMixin_afterSetUp(self)

  def assertLastModifiedHeader(self):
    calculated = rfc1123_date(self.software_instance.getModificationDate())
    self.assertEqual(calculated, self.response.getheader('Last-Modified'))

  def createSoftwareInstance(self, person):
    software_instance = self.cloneByPath(
      'software_instance_module/template_software_instance')
    hosting_subscription = self.cloneByPath(
      'hosting_subscription_module/template_hosting_subscription')
    software_instance.edit(
      reference='SI' + self.test_random_id,
      ssl_key='SSL Key',
      ssl_certificate='SSL Certificate',
      url_string='http://url.of.software.release/'
    )
    software_instance.validate()
    hosting_subscription.edit(
      reference='HS' + self.test_random_id,
      predecessor=software_instance.getRelativeUrl(),
      destination_section=person.getRelativeUrl()
    )
    hosting_subscription.validate()
    hosting_subscription.manage_setLocalRoles(person.getReference(),
      ['Assignee'])
    software_instance.manage_setLocalRoles(person.getReference(),
      ['Assignee'])
    transaction.commit()
    hosting_subscription.recursiveImmediateReindexObject()
    software_instance.recursiveImmediateReindexObject()
    transaction.commit()
    return software_instance

  # needed to avoid calling interaction and being able to destroy XML
  @WorkflowMethod.disable
  def _destroySoftwareInstanceTextContentXml(self, software_instance):
    software_instance.setTextContent('This is bad XML')
    transaction.commit()
    software_instance.recursiveImmediateReindexObject()
    transaction.commit()

@skip('Undecided.')
class TestInstanceGET(SlapOSRestAPIV1InstanceMixin):
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
    self.assertLastModifiedHeader()
    self.assertCacheControlHeader()
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
      "software_release": "http://url.of.software.release/",
      "sla": {"computer_guid": "SOMECOMP"}},
      self.json_response)

  def test_if_modified_since_equal(self):
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance',
      self.software_instance.getRelativeUrl()]),
      headers={'REMOTE_USER': self.customer_reference,
      'If-Modified-Since': rfc1123_date(self.software_instance\
        .getModificationDate())})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(304)

  def test_if_modified_since_after(self):
    # wait three seconds before continuing in order to not hit time precision
    # issue, as test needs to provide date with second precision after
    # last modification of software instance and *before* now()
    time.sleep(3)
    # add 2 seconds, as used rfc1123_date will ceil the second in response and
    # one more second will be required in order to be *after* the modification time
    if_modified = self.software_instance.getModificationDate().timeTime() + 2
    # check the test: is calculated time *before* now?
    self.assertTrue(int(if_modified) < int(DateTime().timeTime()))
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance',
      self.software_instance.getRelativeUrl()]),
      headers={'REMOTE_USER': self.customer_reference,
      'If-Modified-Since': rfc1123_date(DateTime(if_modified))})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(304)

  def test_if_modified_since_before(self):
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance',
      self.software_instance.getRelativeUrl()]),
      headers={'REMOTE_USER': self.customer_reference,
      'If-Modified-Since': rfc1123_date(self.software_instance\
        .getModificationDate() - 1)})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(200)
    self.assertLastModifiedHeader()
    self.assertCacheControlHeader()
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
      "software_release": "http://url.of.software.release/",
      "sla": {"computer_guid": "SOMECOMP"}},
      self.json_response)

  def test_if_modified_since_date_not_date(self):
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance',
      self.software_instance.getRelativeUrl()]),
      headers={'REMOTE_USER': self.customer_reference,
      'If-Modified-Since': 'This Is Not A date'})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(200)
    self.assertLastModifiedHeader()
    self.assertCacheControlHeader()
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
      "software_release": "http://url.of.software.release/",
      "sla": {"computer_guid": "SOMECOMP"}},
      self.json_response)

  def test_if_modified_since_date_future(self):
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance',
      self.software_instance.getRelativeUrl()]),
      headers={'REMOTE_USER': self.customer_reference,
      'If-Modified-Since': rfc1123_date(DateTime() + 1)})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(200)
    self.assertLastModifiedHeader()
    self.assertCacheControlHeader()
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
      "software_release": "http://url.of.software.release/",
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

@skip('Undecided.')
class TestInstanceGETcertificate(SlapOSRestAPIV1InstanceMixin):
  def test(self):
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance',
        self.software_instance.getRelativeUrl(), 'certificate']),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(200)
    self.assertLastModifiedHeader()
    self.assertCacheControlHeader()
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

class TestInstanceAllocableGET(SlapOSRestAPIV1InstanceMixin):
  def test_not_logged_in(self):
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance', 'request']))
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(401)
    self.assertTrue(self.response.getheader('Location') is not None)
    auth = self.response.getheader('WWW-Authenticate')
    self.assertTrue(auth is not None)
    self.assertTrue('Bearer realm="' in auth)

  def test_empty_parameter(self):
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance', 'request']),
      body='{}',
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(400)
    self.assertResponseJson()
    self.assertEqual({
        "slave": "Missing.",
        "software_release": "Missing.",
        "software_type": "Missing.",
        "sla": "Missing."},
      self.json_response)

  def test_bad_sla_json(self):
    kwargs = {
      'software_release': 'http://example.com/example.cfg',
      'sla': 'This is not JSON',
      'software_type': 'type_provided_by_the_software',
      'slave': 'true'}
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance', 'request']) + \
          '?%s' % urllib.urlencode(kwargs),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(400)
    self.assertResponseJson()
    self.assertEqual({'sla': "Malformed value."}, self.json_response)

  def test_slave_not_bool(self):
    kwargs = {
      'software_release': 'http://example.com/example.cfg',
      'sla': json.dumps({
        'computer_id': 'COMP-0'}),
      'software_type': 'type_provided_by_the_software',
      'slave': 'this is not a JSON boolean'}
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance', 'request']) + \
          '?%s' % urllib.urlencode(kwargs),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(400)
    self.assertResponseJson()
    self.assertEqual({
        "slave": "Malformed value.",
        },
      self.json_response)

  def test_correct(self):
    kwargs = {
      'software_release': 'http://example.com/example.cfg',
      'sla': json.dumps({
        'computer_id': 'COMP-0'}),
      'software_type': 'type_provided_by_the_software',
      'slave': 'true'}
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance', 'request']) + \
          '?%s' % urllib.urlencode(kwargs),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(200)
    self.assertResponseJson()

  def test_additional_key_json(self):
    kw_request = {
      'software_release': 'http://example.com/example.cfg',
      'sla': json.dumps({
        'computer_id': 'COMP-0'}),
      'software_type': 'type_provided_by_the_software',
      'slave': 'true'}
    kwargs = kw_request.copy()
    kwargs.update(**{'wrong_key': 'Be ignored'})
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance', 'request']) + \
          '?%s' % urllib.urlencode(kwargs),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(200)
    self.assertResponseJson()

#   def test_correct_server_side_raise(self):
#     self.customer.requestSoftwareInstance = \
#       RaisingSimulator(AttributeError)
#     transaction.commit()
#     kwargs = {
#       'parameter': {
#         'Custom1': 'one string',
#         'Custom2': 'one float',
#         'Custom3': ['abc', 'def']},
#       'title': 'My unique instance',
#       'software_release': 'http://example.com/example.cfg',
#       'status': 'started',
#       'sla': {
#         'computer_id': 'COMP-0'},
#       'software_type': 'type_provided_by_the_software',
#       'slave': True}
#     self.connection.request(method='GET',
#       url='/'.join([self.api_path, 'instance', 'request']),
#       body=json.dumps(kwargs),
#       headers={'REMOTE_USER': self.customer_reference})
#     self.prepareResponse()
#     self.assertBasicResponse()
#     self.assertResponseCode(500)
#     self.assertResponseJson()
#     self.assertEqual({
#         "error": "There is system issue, please try again later.",
#         },
#       self.json_response)

#   def test_content_negotiation_headers(self):
#     self.connection = CustomHeaderHTTPConnection(host=self.api_netloc,
#       custom_header={
#         'Access-Control-Request-Headers': self.access_control_allow_headers
#       })
#     kwargs = {
#       'parameter': {
#         'Custom1': 'one string',
#         'Custom2': 'one float',
#         'Custom3': ['abc', 'def']},
#       'title': 'My unique instance',
#       'software_release': 'http://example.com/example.cfg',
#       'status': 'started',
#       'sla': {
#         'computer_id': 'COMP-0'},
#       'software_type': 'type_provided_by_the_software',
#       'slave': True}
#     self.connection.request(method='GET',
#       url='/'.join([self.api_path, 'instance', 'request']),
#       body=json.dumps(kwargs),
#       headers={'REMOTE_USER': self.customer_reference})
#     self.prepareResponse()
#     self.assertBasicResponse()
#     self.assertResponseCode(400)
#     self.assertResponseJson()
#     self.assertEqual({
#       'Content-Type': "Header with value '^application/json.*' is required."},
#       self.json_response)
# 
#     # now check with incorrect headers
#     self.connection.request(method='GET',
#       url='/'.join([self.api_path, 'instance', 'request']),
#       body=json.dumps(kwargs),
#       headers={'REMOTE_USER': self.customer_reference,
#         'Content-Type': 'please/complain',
#         'Accept': 'be/silent'})
#     self.prepareResponse()
#     self.assertBasicResponse()
#     self.assertResponseCode(400)
#     self.assertResponseJson()
#     self.assertEqual({
#       'Content-Type': "Header with value '^application/json.*' is required."},
#       self.json_response)
#     # and with correct ones are set by default

def SlapOSRestAPIV1BangMixin_afterSetUp(self):
  SlapOSRestAPIV1BangMixin_afterSetUp(self)
  self.instance_bang_simulator = tempfile.mkstemp()[1]
  self.software_instance.bang = Simulator(
    self.instance_bang_simulator, 'bang')
  transaction.commit()

def SlapOSRestAPIV1BangMixin_beforeTearDown(self):
  SlapOSRestAPIV1BangMixin_beforeTearDown()
  if os.path.exists(self.instance_bang_simulator):
    os.unlink(self.instance_bang_simulator)

class SlapOSRestAPIV1BangMixin(SlapOSRestAPIV1InstanceMixin):
  def afterSetUp(self):
    self._afterSetUp()
    SlapOSRestAPIV1BangMixin_afterSetUp(self)

  def beforeTearDown(self):
    SlapOSRestAPIV1BangMixin_beforeTearDown(self)

  def assertInstanceBangSimulatorEmpty(self):
    self.assertEqual(open(self.instance_bang_simulator).read(), '')

  def assertInstanceBangSimulator(self, args, kwargs):
    stored = eval(open(self.instance_bang_simulator).read())
    # do the same translation magic as in workflow
    kwargs['comment'] = kwargs.pop('log')
    self.assertEqual(stored,
      [{'recargs': args, 'reckwargs': kwargs,
      'recmethod': 'bang'}])

@skip('Undecided.')
class TestInstancePOSTbang(SlapOSRestAPIV1BangMixin):
  def test(self):
    kwargs = {'log': 'This is cool log!', 'bang_tree': True}
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance',
      self.software_instance.getRelativeUrl(), 'bang']),
      body=json.dumps(kwargs),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(204)
    self.assertInstanceBangSimulator((), kwargs)

  def test_server_side_raise(self):
    self.software_instance.bang = RaisingSimulator(
      AttributeError)
    transaction.commit()
    kwargs = {'log': 'This is cool log!'}
    self.connection.request(method='POST',
      url='/'.join([self.api_path, 'instance',
      self.software_instance.getRelativeUrl(), 'bang']),
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
    self.assertInstanceBangSimulatorEmpty()

  def test_bad_xml(self):
    self._destroySoftwareInstanceTextContentXml(self.software_instance)
    kwargs = {'log': 'This is cool log!', 'bang_tree': True}
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
    kw_log = {'log': 'This is cool log!', 'bang_tree': True}
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
    self.assertEqual({'log': 'bool is not unicode.'}, self.json_response)
    self.assertInstanceBangSimulatorEmpty()

@skip('Undecided.')
class TestInstancePUT(SlapOSRestAPIV1InstanceMixin):
  def afterSetUp(self):
    super(TestInstancePUT, self).afterSetUp()
    self.instance_put_simulator = tempfile.mkstemp()[1]
    self.software_instance.setTitle = Simulator(self.instance_put_simulator,
      'setTitle')
    self.software_instance.setConnectionXml = Simulator(self.instance_put_simulator,
      'setConnectionXml')
    transaction.commit()

  def beforeTearDown(self):
    super(TestInstancePUT, self).beforeTearDown()
    if os.path.exists(self.instance_put_simulator):
      os.unlink(self.instance_put_simulator)

  def assertInstancePUTSimulator(self, l):
    stored = eval(open(self.instance_put_simulator).read())
    self.assertEqual(stored, l)
    self.assertEqual(
      set([type(q) for q in l[0]['recargs']]),
      set([str])
    )

  def assertInstancePUTSimulatorEmpty(self):
    self.assertEqual('', open(self.instance_put_simulator).read())

  def test(self):
    d = {
      'title': 'New Title' + self.test_random_id,
      'connection': {'url': 'http://new' + self.test_random_id}
    }
    self.connection.request(method='PUT',
      url='/'.join([self.api_path, 'instance',
        self.software_instance.getRelativeUrl()]),
      body=json.dumps(d),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(200)
    self.assertResponseJson()
    self.assertEqual({
      "title": "Modified.",
      "connection": "Modified."
      },
      self.json_response)
    self.assertInstancePUTSimulator([{'recargs': (d['title'],), 'reckwargs': {},
      'recmethod': 'setTitle'},
    {'recargs': ('<?xml version=\'1.0\' encoding=\'utf-8\'?>\n<instance>\n  '\
      '<parameter id="url">http://new%s</parameter>\n</instance>\n'%
        self.test_random_id,), 'reckwargs': {}, 'recmethod': 'setConnectionXml'}])

  def test_same_title(self):
    d = {
      'title': self.software_instance.getTitle(),
      'connection': {'url': 'http://new' + self.test_random_id}
    }
    self.connection.request(method='PUT',
      url='/'.join([self.api_path, 'instance',
        self.software_instance.getRelativeUrl()]),
      body=json.dumps(d),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(200)
    self.assertResponseJson()
    self.assertEqual({"connection": "Modified."}, self.json_response)
    self.assertInstancePUTSimulator([
      {'recargs': ('<?xml version=\'1.0\' encoding=\'utf-8\'?>\n<instance>\n  '\
      '<parameter id="url">http://new%s</parameter>\n</instance>\n'%
        self.test_random_id,), 'reckwargs': {}, 'recmethod': 'setConnectionXml'}])

  def test_same_connection(self):
    d = {
      'title': 'New Title 2' + self.test_random_id,
      'connection': self.software_instance.getConnectionXmlAsDict()
    }
    self.connection.request(method='PUT',
      url='/'.join([self.api_path, 'instance',
        self.software_instance.getRelativeUrl()]),
      body=json.dumps(d),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(200)
    self.assertResponseJson()
    self.assertEqual({
      "title": "Modified.",
      },
      self.json_response)
    self.assertInstancePUTSimulator([{'recargs': (d['title'],),
      'reckwargs': {}, 'recmethod': 'setTitle'}])

  def test_same_title_connection(self):
    d = {
      'title': self.software_instance.getTitle(),
      'connection': self.software_instance.getConnectionXmlAsDict()
    }
    self.connection.request(method='PUT',
      url='/'.join([self.api_path, 'instance',
        self.software_instance.getRelativeUrl()]),
      body=json.dumps(d),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(204)
    self.assertInstancePUTSimulatorEmpty()

  def test_not_logged_in(self):
    self.connection.request(method='PUT',
      url='/'.join([self.api_path, 'instance',
        self.software_instance.getRelativeUrl()]))
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(401)
    self.assertTrue(self.response.getheader('Location') is not None)
    auth = self.response.getheader('WWW-Authenticate')
    self.assertTrue(auth is not None)
    self.assertTrue('Bearer realm="' in auth)
    self.assertInstancePUTSimulatorEmpty()

  def test_no_json(self):
    self.connection.request(method='PUT',
      url='/'.join([self.api_path, 'instance',
        self.software_instance.getRelativeUrl()]),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(400)
    self.assertResponseJson()
    self.assertEqual({'error': "Data is not json object."}, self.json_response)
    self.assertInstancePUTSimulatorEmpty()

  def test_bad_json(self):
    self.connection.request(method='PUT',
      url='/'.join([self.api_path, 'instance',
        self.software_instance.getRelativeUrl()]),
      body='This is not JSON',
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(400)
    self.assertResponseJson()
    self.assertEqual({'error': "Data is not json object."}, self.json_response)
    self.assertInstancePUTSimulatorEmpty()

  def test_empty_json(self):
    self.connection.request(method='PUT',
      url='/'.join([self.api_path, 'instance',
        self.software_instance.getRelativeUrl()]),
      body='{}',
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(204)
    self.assertInstancePUTSimulatorEmpty()

  def test_future_compat(self):
    self.connection.request(method='PUT',
      url='/'.join([self.api_path, 'instance',
        self.software_instance.getRelativeUrl()]),
      body=json.dumps({'ignore':'me'}),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(204)
    self.assertInstancePUTSimulatorEmpty()

@skip('Undecided.')
class TestInstanceGETlist(SlapOSRestAPIV1InstanceMixin):
  def assertLastModifiedHeader(self):
    calculated = rfc1123_date(self.portal.software_instance_module\
      .bobobase_modification_time())
    self.assertEqual(calculated, self.response.getheader('Last-Modified'))

  def test_no_cache(self):
    # version of test which ignores cache to expose possible other errors
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance']),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(200)
    self.assertResponseJson()
    self.assertEqual({
      "list": ['/'.join([self.api_url, 'instance',
        self.software_instance.getRelativeUrl()])]
      },
      self.json_response)

  def test(self):
    self.test_no_cache()
    self.assertLastModifiedHeader()
    self.assertCacheControlHeader()

  def test_if_modified_since_equal(self):
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance']),
      headers={'REMOTE_USER': self.customer_reference,
      'If-Modified-Since': rfc1123_date(self.portal.software_instance_module\
        .bobobase_modification_time())})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(304)

  def test_if_modified_since_after(self):
    # wait three seconds before continuing in order to not hit time precision
    # issue, as test needs to provide date with second precision after
    # last modification of software instance and *before* now()
    time.sleep(3)
    # add 2 seconds, as used rfc1123_date will ceil the second in response and
    # one more second will be required in order to be *after* the modification time
    if_modified = self.portal.software_instance_module\
      .bobobase_modification_time().timeTime() + 2
    # check the test: is calculated time *before* now?
    self.assertTrue(int(if_modified) < int(DateTime().timeTime()))
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance']),
      headers={'REMOTE_USER': self.customer_reference,
      'If-Modified-Since': rfc1123_date(self.portal.software_instance_module\
        .bobobase_modification_time())})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(304)

  def test_if_modified_since_before(self):
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance']),
      headers={'REMOTE_USER': self.customer_reference,
      'If-Modified-Since': rfc1123_date(self.portal.software_instance_module\
        .bobobase_modification_time() - 1)})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(200)
    self.assertResponseJson()
    self.assertLastModifiedHeader()
    self.assertCacheControlHeader()
    self.assertEqual({
      "list": ['/'.join([self.api_url, 'instance',
        self.software_instance.getRelativeUrl()])]
      },
      self.json_response)

  def test_if_modified_since_date_not_date(self):
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance']),
      headers={'REMOTE_USER': self.customer_reference,
      'If-Modified-Since': 'This Is Not A date'})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(200)
    self.assertResponseJson()
    self.assertLastModifiedHeader()
    self.assertCacheControlHeader()
    self.assertEqual({
      "list": ['/'.join([self.api_url, 'instance',
        self.software_instance.getRelativeUrl()])]
      },
      self.json_response)

  def test_if_modified_since_date_future(self):
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance']),
      headers={'REMOTE_USER': self.customer_reference,
      'If-Modified-Since': rfc1123_date(DateTime() + 1)})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(200)
    self.assertResponseJson()
    self.assertLastModifiedHeader()
    self.assertCacheControlHeader()
    self.assertEqual({
      "list": ['/'.join([self.api_url, 'instance',
        self.software_instance.getRelativeUrl()])]
      },
      self.json_response)

  def test_another_one(self):
    person, person_reference = self.createPerson()
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance']),
      headers={'REMOTE_USER': person_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(204)

  def test_empty(self):
    self.portal.portal_catalog.unindexObject(
      uid=self.software_instance.getUid())
    self.software_instance.getParentValue().deleteContent(
      self.software_instance.getId())
    transaction.commit()

    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance']),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(204)

  def test_not_logged_in(self):
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'instance']))
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(401)
    self.assertTrue(self.response.getheader('Location') is not None)
    auth = self.response.getheader('WWW-Authenticate')
    self.assertTrue(auth is not None)
    self.assertTrue('Bearer realm="' in auth)
    self.assertPersonRequestSimulatorEmpty()

@skip('Undecided.')
class TestComputerPUT(SlapOSRestAPIV1MixinBase):
  def createComputer(self):
    computer = self.cloneByPath(
      'computer_module/template_computer')
    computer.edit(reference='C' + self.test_random_id)
    computer.validate()
    computer.manage_setLocalRoles(computer.getReference(),
      ['Assignor'])
    transaction.commit()
    computer.recursiveImmediateReindexObject()
    transaction.commit()
    return computer

  def afterSetUp(self):
    super(TestComputerPUT, self).afterSetUp()
    self.computer = self.createComputer()
    self.computer_reference = self.computer.getReference()
    self.computer_put_simulator = tempfile.mkstemp()[1]
    self.computer.Computer_updateFromJson = Simulator(self.computer_put_simulator,
      'Computer_updateFromJson')
    transaction.commit()

  def beforeTearDown(self):
    super(TestComputerPUT, self).beforeTearDown()
    if os.path.exists(self.computer_put_simulator):
      os.unlink(self.computer_put_simulator)

  def assertComputerPUTSimulator(self, l):
    stored = eval(open(self.computer_put_simulator).read())
    self.assertEqual(stored, l)
    # check that method is called with strings, not unicodes
    for l_ in l[0]['recargs'][0].itervalues():
      for el in l_:
        self.assertEqual(
          set([type(q) for q in el.itervalues()]),
          set([str])
        )

  def assertComputerPUTSimulatorEmpty(self):
    self.assertEqual('', open(self.computer_put_simulator).read())

  def test(self):
    d = {
      "partition": [
        {
          "title": "part0",
          "public_ip": "::0",
          "private_ip": "127.0.0.0",
          "tap_interface": "tap0"
        }
      ],
      "software": [
        {
          "software_release": "software_release",
          "status": "uninstalled",
          "log": "Installation log"
        }
      ]
    }

    self.connection.request(method='PUT',
      url='/'.join([self.api_path, 'computer',
        self.computer.getRelativeUrl()]),
      body=json.dumps(d),
      headers={'REMOTE_USER': self.computer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(204)
    self.assertComputerPUTSimulator([
      {'recmethod': 'Computer_updateFromJson',
      'recargs': ({
        'partition':
          [{
            'public_ip': '::0',
            'tap_interface': 'tap0',
            'private_ip': '127.0.0.0',
            'title': 'part0'}],
        'software':
          [{
            'status': 'uninstalled',
            'software_release': 'software_release',
            'log': 'Installation log'}]},),
      'reckwargs': {}}])

  def test_not_logged_in(self):
    self.connection.request(method='PUT',
      url='/'.join([self.api_path, 'computer',
        self.computer.getRelativeUrl()]))
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(401)
    self.assertTrue(self.response.getheader('Location') is not None)
    auth = self.response.getheader('WWW-Authenticate')
    self.assertTrue(auth is not None)
    self.assertTrue('Bearer realm="' in auth)
    self.assertComputerPUTSimulatorEmpty()

  def test_no_json(self):
    self.connection.request(method='PUT',
      url='/'.join([self.api_path, 'computer',
        self.computer.getRelativeUrl()]),
      headers={'REMOTE_USER': self.computer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(400)
    self.assertResponseJson()
    self.assertEqual({'error': "Data is not json object."}, self.json_response)
    self.assertComputerPUTSimulatorEmpty()

  def test_bad_json(self):
    self.connection.request(method='PUT',
      url='/'.join([self.api_path, 'computer',
        self.computer.getRelativeUrl()]),
      body='This is not JSON',
      headers={'REMOTE_USER': self.computer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(400)
    self.assertResponseJson()
    self.assertEqual({'error': "Data is not json object."}, self.json_response)
    self.assertComputerPUTSimulatorEmpty()

  def test_empty_json(self):
    self.connection.request(method='PUT',
      url='/'.join([self.api_path, 'computer',
        self.computer.getRelativeUrl()]),
      body='{}',
      headers={'REMOTE_USER': self.computer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(204)
    self.assertComputerPUTSimulatorEmpty()

  def test_future_compat(self):
    self.connection.request(method='PUT',
      url='/'.join([self.api_path, 'computer',
        self.computer.getRelativeUrl()]),
      body=json.dumps({'ignore':'me'}),
      headers={'REMOTE_USER': self.computer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(204)
    self.assertComputerPUTSimulatorEmpty()

  def test_software_release_status(self):
    d = {
      "partition": [
        {
          "title": "part0",
          "public_ip": "::0",
          "private_ip": "127.0.0.0",
          "tap_interface": "tap0"
        }
      ],
      "software": [
        {
          "software_release": "software_release",
          "status": "wrong status",
          "log": "Installation log"
        }
      ]
    }

    self.connection.request(method='PUT',
      url='/'.join([self.api_path, 'computer',
        self.computer.getRelativeUrl()]),
      body=json.dumps(d),
      headers={'REMOTE_USER': self.computer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(400)
    self.assertResponseJson()
    self.assertEqual({'software_0': ['Status "wrong status" is incorrect.']},
      self.json_response)
    self.assertComputerPUTSimulatorEmpty()

  def test_only_partition(self):
    d = {
      "partition": [
        {
          "title": "part0",
          "public_ip": "::0",
          "private_ip": "127.0.0.0",
          "tap_interface": "tap0"
        }
      ]
    }

    self.connection.request(method='PUT',
      url='/'.join([self.api_path, 'computer',
        self.computer.getRelativeUrl()]),
      body=json.dumps(d),
      headers={'REMOTE_USER': self.computer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(204)
    self.assertComputerPUTSimulator([
      {'recmethod': 'Computer_updateFromJson',
      'recargs': ({
        'partition':
          [{
            'public_ip': '::0',
            'tap_interface': 'tap0',
            'private_ip': '127.0.0.0',
            'title': 'part0'}],
        },),
      'reckwargs': {}}])

  def test_only_software(self):
    d = {
      "software": [
        {
          "software_release": "software_release",
          "status": "uninstalled",
          "log": "Installation log"
        }
      ]
    }

    self.connection.request(method='PUT',
      url='/'.join([self.api_path, 'computer',
        self.computer.getRelativeUrl()]),
      body=json.dumps(d),
      headers={'REMOTE_USER': self.computer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(204)
    self.assertComputerPUTSimulator([
      {'recmethod': 'Computer_updateFromJson',
      'recargs': ({
        'software':
          [{
            'status': 'uninstalled',
            'software_release': 'software_release',
            'log': 'Installation log'}]},),
      'reckwargs': {}}])

  def test_partition_object_incorrect(self):
    d = {
      "partition": [
        {
          "title": "part0",
          "public_ip": "::0",
          "private_ip": "127.0.0.0"
        }
      ],
      "software": [
        {
          "software_release": "software_release",
          "status": "uninstalled",
          "log": "Installation log"
        }
      ]
    }

    self.connection.request(method='PUT',
      url='/'.join([self.api_path, 'computer',
        self.computer.getRelativeUrl()]),
      body=json.dumps(d),
      headers={'REMOTE_USER': self.computer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(400)
    self.assertResponseJson()
    self.assertEqual({'partition_0': ['Missing key "tap_interface".']},
      self.json_response)
    self.assertComputerPUTSimulatorEmpty()

  def test_software_object_incorrect(self):
    d = {
      "partition": [
        {
          "title": "part0",
          "public_ip": "::0",
          "private_ip": "127.0.0.0",
          "tap_interface": "tap0"
        }
      ],
      "software": [
        {
          "software_release": "software_release",
          "status": "uninstalled",
        }
      ]
    }

    self.connection.request(method='PUT',
      url='/'.join([self.api_path, 'computer',
        self.computer.getRelativeUrl()]),
      body=json.dumps(d),
      headers={'REMOTE_USER': self.computer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(400)
    self.assertResponseJson()
    self.assertEqual({'software_0': ['Missing key "log".']},
      self.json_response)
    self.assertComputerPUTSimulatorEmpty()

class TestStatusGET(SlapOSRestAPIV1InstanceMixin):
  def afterSetUp(self):
    self._afterSetUp()
    SlapOSRestAPIV1Mixin_afterSetUp(self)

  def createComputer(self):
    computer = self.cloneByPath(
      'computer_module/template_computer')
    computer.edit(reference='C' + self.test_random_id)
    computer.validate()
    computer.manage_setLocalRoles(self.customer_reference,
      ['Assignee'])
    transaction.commit()
    computer.recursiveImmediateReindexObject()
    transaction.commit()
    return computer

  def assertCacheControlHeader(self):
    self.assertEqual('max-age=300, private',
      self.response.getheader('Cache-Control'))

  def test_non_existing_status(self):
    non_existing = 'system_event_module/' + self.generateNewId()
    try:
      self.portal.restrictedTraverse(non_existing)
    except KeyError:
      pass
    else:
      raise AssertionError('It was impossible to test')
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'status',
      non_existing]),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(404)

  def test_something_else(self):
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'status',
      self.customer.getRelativeUrl()]),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(404)

  def _storeJson(self, key, json):
    memcached_dict = self.getPortalObject().portal_memcached.\
      getMemcachedDict(
        key_prefix='slap_tool',
        plugin_path='portal_memcached/default_memcached_plugin')
    memcached_dict[key] = json

  def test_on_computer(self):
    self.computer = self.createComputer()
    reference = self.computer.getReference()
    value = json.dumps({'foo': reference})
    self._storeJson(reference, value)
    transaction.commit()
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'status',
      self.computer.getRelativeUrl()]),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(200)
    self.assertCacheControlHeader()
    self.assertResponseJson()
    value = json.loads(value)
    value['@document'] = self.computer.getRelativeUrl()
    self.assertEqual(value, self.json_response)

  def test_on_instance(self):
    self.software_instance = self.createSoftwareInstance(self.customer)
    reference = self.software_instance.getReference()
    value = json.dumps({'bar': reference})
    self._storeJson(reference, value)
    transaction.commit()
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'status',
      self.software_instance.getRelativeUrl()]),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(200)
    self.assertCacheControlHeader()
    self.assertResponseJson()
    value = json.loads(value)
    value['@document'] = self.software_instance.getRelativeUrl()
    self.assertEqual(value, self.json_response)

  def test_no_data_in_memcached(self):
    self.computer = self.createComputer()
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'status',
      self.computer.getRelativeUrl()]),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(200)
    self.assertCacheControlHeader()
    self.assertResponseJson()
    self.assertEquals(self.json_response['user'], 'SlapOS Master')

  def test_search_no_status(self):
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'status']),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(204)

  def test_search_existing_instance(self):
    self.software_instance = self.createSoftwareInstance(self.customer)
    transaction.commit()
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'status']),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(200)
    self.assertCacheControlHeader()
    self.assertResponseJson()
    self.assertEqual({
      'list': ['/'.join([self.api_url, 'status',
                         self.software_instance.getRelativeUrl()])]
      }, self.json_response)

  def test_check_no_destroyed_instance(self):
    self.software_instance = self.createSoftwareInstance(self.customer)
    self.software_instance.edit(slap_state='destroy_requested')
    transaction.commit()
    self.connection.request(method='GET',
      url='/'.join([self.api_path, 'status']),
      headers={'REMOTE_USER': self.customer_reference})
    self.prepareResponse()
    self.assertBasicResponse()
    self.assertResponseCode(200)
    self.assertCacheControlHeader()
    self.assertResponseJson()
    self.assertEqual({
      'list': []
      }, self.json_response)


