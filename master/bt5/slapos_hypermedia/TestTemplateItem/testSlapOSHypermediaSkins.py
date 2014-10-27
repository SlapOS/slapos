# -*- coding: utf-8 -*-
# Copyright (c) 2002-2013 Nexedi SA and Contributors. All Rights Reserved.
import transaction
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
from zExceptions import Unauthorized
from Products.ERP5Type.tests.utils import createZODBPythonScript
from Products.ERP5Type.tests.backportUnittest import skip
from functools import wraps

from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse

import os
import sys

import json
import StringIO

def changeSkin(skin_name):
  def decorator(func):
    def wrapped(self, *args, **kwargs):
      default_skin = self.portal.portal_skins.default_skin
      self.portal.portal_skins.changeSkin(skin_name)
      self.app.REQUEST.set('portal_skin', skin_name)
      try:
        v = func(self, *args, **kwargs)
      finally:
        self.portal.portal_skins.changeSkin(default_skin)
        self.app.REQUEST.set('portal_skin', default_skin)
      return v
    return wrapped
  return decorator

def simulate(script_id, params_string, code_string):
  def upperWrap(f):
    @wraps(f)
    def decorated(self, *args, **kw):
      if script_id in self.portal.portal_skins.custom.objectIds():
        raise ValueError('Precondition failed: %s exists in custom' % script_id)
      createZODBPythonScript(self.portal.portal_skins.custom,
                          script_id, params_string, code_string)
      try:
        result = f(self, *args, **kw)
      finally:
        if script_id in self.portal.portal_skins.custom.objectIds():
          self.portal.portal_skins.custom.manage_delObjects(script_id)
        transaction.commit()
      return result
    return decorated
  return upperWrap

def do_fake_request(request_method, headers={}):
  __version__ = "0.1"
  env={}
  env['SERVER_NAME']='bobo.server'
  env['SERVER_PORT']='80'
  env['REQUEST_METHOD']=request_method
  env['REMOTE_ADDR']='204.183.226.81 '
  env['REMOTE_HOST']='bobo.remote.host'
  env['HTTP_USER_AGENT']='Bobo/%s' % __version__
  env['HTTP_HOST']='127.0.0.1'
  env['SERVER_SOFTWARE']='Bobo/%s' % __version__
  env['SERVER_PROTOCOL']='HTTP/1.0 '
  env['HTTP_ACCEPT']='image/gif, image/x-xbitmap, image/jpeg, */* '
  env['SERVER_HOSTNAME']='bobo.server.host'
  env['GATEWAY_INTERFACE']='CGI/1.1 '
  env['SCRIPT_NAME']='Main'
  env.update(headers)
  return HTTPRequest(StringIO.StringIO(), env, HTTPResponse())

from Products.ERP5Type.tests.ERP5TypeTestCase import ERP5TypeTestCase
class ERP5HALJSONStyleSkinsMixin(ERP5TypeTestCase):
  def afterSetUp(self):
    self.login()
    self.changeSkin('Hal')

  def beforeTearDown(self):
    transaction.abort()

class TestBase_getRequestHeader(ERP5HALJSONStyleSkinsMixin):
  def test_getRequestHeader_REQUEST_disallowed(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Base_getRequestHeader,
      "foo",
      REQUEST={})

  def test_getRequestHeader_key_error(self):
    self.assertEquals(
        self.portal.Base_getRequestHeader('foo'),
        None
        )

  def test_getRequestHeader_default_value(self):
    self.assertEquals(
        self.portal.Base_getRequestHeader('foo', default='bar'),
        'bar'
        )

  @skip('TODO')
  def test_getRequestHeader_matching_key(self):
    pass

# XXX to be migrated to erp5_hal_json_style bt
class TestBase_getRequestUrl(ERP5HALJSONStyleSkinsMixin):
  def test_getRequestUrl_REQUEST_disallowed(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Base_getRequestUrl,
      REQUEST={})

  @skip('TODO')
  def test_getRequestUrl_matching_key(self):
    pass

class TestBase_getRequestBody(ERP5HALJSONStyleSkinsMixin):
  def test_getRequestBody_REQUEST_disallowed(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Base_getRequestBody,
      REQUEST={})

  @skip('TODO')
  def test_getRequestBody_matching_key(self):
    pass

class TestBase_handleAcceptHeader(ERP5HALJSONStyleSkinsMixin):
  def test_handleAcceptHeader_REQUEST_disallowed(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Base_handleAcceptHeader,
      [],
      REQUEST={})

  @simulate('Base_getRequestHeader', '*args, **kwargs', 'return "*/*"')
  @changeSkin('Hal')
  def test_handleAcceptHeader_star_accept(self):
    self.assertEquals(
        self.portal.Base_handleAcceptHeader(['application/vnd+test',
                                             'application/vnd+test2']),
        'application/vnd+test'
        )

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/vnd+2test"')
  @changeSkin('Hal')
  def test_handleAcceptHeader_matching_type(self):
    self.assertEquals(
        self.portal.Base_handleAcceptHeader(['application/vnd+test',
                                             'application/vnd+2test']),
        'application/vnd+2test'
        )

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/vnd+2test"')
  @changeSkin('Hal')
  def test_handleAcceptHeader_non_matching_type(self):
    self.assertEquals(
        self.portal.Base_handleAcceptHeader(['application/vnd+test']),
        None
        )


class TestSlapOSHypermediaMixin(testSlapOSMixin):
  def afterSetUp(self):
    testSlapOSMixin.afterSetUp(self)
    self.changeSkin('Hal')

  def beforeTearDown(self):
    transaction.abort()

  def _makePerson(self):
    new_id = self.generateNewId()
    person_user = self.portal.person_module.template_member.\
                                 Base_createCloneDocument(batch_mode=1)
    person_user.edit(
      title="live_test_%s" % new_id,
      reference="live_test_%s" % new_id,
      default_email_text="live_test_%s@example.org" % new_id,
    )

    person_user.validate()
    for assignment in person_user.contentValues(portal_type="Assignment"):
      assignment.open()
    self.tic()
    self.changeSkin('Hal')
    return person_user

  def _makeHostingSubscription(self):
    hosting_subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    hosting_subscription.validate()
    self.tic()
    self.changeSkin('Hal')
    return hosting_subscription

  def _makeInstance(self):
    instance = self.portal.software_instance_module\
        .template_software_instance.Base_createCloneDocument(batch_mode=1)
    instance.validate()
    self.tic()
    return instance

  def _makeComputer(self):
    computer = self.portal.computer_module\
        .template_computer.Base_createCloneDocument(batch_mode=1)
    computer.validate()
    self.tic()
    return computer

  def _makeSoftwareInstallation(self):
    software_installation = self.portal.software_installation_module\
        .template_software_installation.Base_createCloneDocument(batch_mode=1)
    software_installation.validate()
    self.tic()
    return software_installation

class TestSlapOSPersonERP5Document_getHateoas(TestSlapOSHypermediaMixin):
  # XXX: currently for person, make it generic

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/vnd+bar"')
  @changeSkin('Hal')
  def test_getHateoasPerson_wrong_ACCEPT(self):
    person_user = self._makePerson()
    fake_request = do_fake_request("GET")
    result = person_user.ERP5Document_getHateoas(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 406)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoasPerson_bad_method(self):
    person_user = self._makePerson()
    fake_request = do_fake_request("POST")
    result = person_user.ERP5Document_getHateoas(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 405)
    self.assertEquals(result, "")


  @simulate('Base_getRequestUrl', '*args, **kwargs',
      'return "http://example.org/bar"')
  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoasPerson_result(self):
    person_user = self._makePerson()
    fake_request = do_fake_request("GET")
    result = person_user.ERP5Document_getHateoas(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/hal+json"
    )
    results = json.loads(result)
    action_object_slap = results['_links']['action_object_slap']
    self.assertEqual(len(action_object_slap), 3)
    for action in [
      {
        'href': '%s/Person_getHateoasComputerList' % \
          person_user.absolute_url(),
        'name': 'get_hateoas_computer_list',
        'title': 'getHateoasComputerList'
      },
      {
        'href': '%s/Person_getHateoasHostingSubscriptionList' % \
          person_user.absolute_url(),
        'name': 'get_hateoas_hosting_subscription_list',
        'title': 'getHateoasHostingSubscriptionList'
      },
      {
        'href': '%s/Person_getHateoasInformation' % \
          person_user.absolute_url(),
        'name': 'get_hateoas_information',
        'title': 'getHateoasInformation'
      },
    ]:
      self.assertTrue(action in action_object_slap)
    self.assertEquals(results['_links']['action_object_slap_post'], {
        "href": '%s/Person_requestHateoasHostingSubscription' %  \
          person_user.absolute_url(),
        "name": "request_hateoas_hosting_subscription",
        "title": "requestHateoasHostingSubscription"
    })

class TestSlapOSBase_getHateoasMaster(TestSlapOSHypermediaMixin):

  @changeSkin('Hal')
  def test_getHateoasMaster_REQUEST_mandatory(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Base_getHateoasMaster
    )

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/vnd+bar"')
  @changeSkin('Hal')
  def test_getHateoasMaster_wrong_ACCEPT(self):
    #self.changeSkin('Hal')
    fake_request = do_fake_request("GET")
    result = self.portal.Base_getHateoasMaster(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 406)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoasMaster_bad_method(self):
    fake_request = do_fake_request("POST")
    result = self.portal.Base_getHateoasMaster(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 405)
    self.assertEquals(result, "")

  @simulate('Base_getRequestUrl', '*args, **kwargs',
      'return "http://example.org/bar"')
  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoasMaster_anonymous_result(self):
    self.logout()
    self.changeSkin('Hal')
    fake_request = do_fake_request("GET")
    result = self.portal.Base_getHateoasMaster(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/hal+json"
    )
    self.assertEquals(result, json.dumps({
      '_links': {
        "self": {
          "href": "http://example.org/bar"
        },
      },
    }, indent=2))

  @simulate('Base_getRequestUrl', '*args, **kwargs',
      'return "http://example.org/bar"')
  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoasMaster_person_result(self):
    person_user = self._makePerson()
    self.login(person_user.getReference())
    self.changeSkin('Hal')
    fake_request = do_fake_request("GET")
    result = self.portal.Base_getHateoasMaster(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/hal+json"
    )
    self.assertEquals(result, json.dumps({
      '_links': {
        "self": {
          "href": "http://example.org/bar"
        },
        "action_object_jump": {
          "href": "%s/ERP5Document_getHateoas" % person_user.absolute_url(),
          "title": "Person"
        },
      },
    }, indent=2))

  @simulate('Base_getRequestUrl', '*args, **kwargs',
      'return "http://example.org/bar"')
  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoasMaster_instance_result(self):
    self._makeTree()
    self.login(self.software_instance.getReference())
    self.changeSkin('Hal')
    fake_request = do_fake_request("GET")
    result = self.portal.Base_getHateoasMaster(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/hal+json"
    )
    self.assertEquals(result, json.dumps({
      '_links': {
        "self": {
          "href": "http://example.org/bar"
        },
        "action_object_jump": {
          "href": "%s/ERP5Document_getHateoas" % self.software_instance.absolute_url(),
          "title": "Software Instance"
        },
      },
    }, indent=2))

class TestSlapOSPerson_requestHateoasHostingSubscription(TestSlapOSHypermediaMixin):

  @changeSkin('Hal')
  def test_requestHateoasHostingSubscription_REQUEST_mandatory(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Person_requestHateoasHostingSubscription
    )

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/vnd+bar"')
  @changeSkin('Hal')
  def test_requestHateoasHostingSubscription_wrong_CONTENT(self):
    person_user = self._makePerson()
    fake_request = do_fake_request("POST")
    result = person_user.Person_requestHateoasHostingSubscription(
      REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 406)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/json"')
  @changeSkin('Hal')
  def test_requestHateoasHostingSubscription_bad_method(self):
    person_user = self._makePerson()
    fake_request = do_fake_request("GET")
    result = person_user.Person_requestHateoasHostingSubscription(
      REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 405)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/json"')
  @changeSkin('Hal')
  def test_requestHateoasHostingSubscription_not_person_context(self):
    fake_request = do_fake_request("POST")
    result = self.portal.Person_requestHateoasHostingSubscription(
      REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 403)
    self.assertEquals(result, "")

  @simulate('Base_getRequestBody', '*args, **kwargs',
            'return "[}"')
  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/json"')
  @changeSkin('Hal')
  def test_requestHateoasHostingSubscription_no_json(self):
    person_user = self._makePerson()
    fake_request = do_fake_request("POST")
    result = person_user.Person_requestHateoasHostingSubscription(
      REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 400)
    self.assertEquals(result, "")

  @simulate('Base_getRequestBody', '*args, **kwargs',
            'return "%s"' % json.dumps({
              }))
  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/json"')
  @changeSkin('Hal')
  def test_requestHateoasHostingSubscription_missing_parameter(self):
    person_user = self._makePerson()
    fake_request = do_fake_request("POST")
    result = person_user.Person_requestHateoasHostingSubscription(
      REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 400)
    self.assertEquals(result, "")

  @simulate('Base_getRequestBody', '*args, **kwargs',
            'return """%s"""' % json.dumps({
  'software_release': 'http://example.orgé',
  'title': 'a great titleé',
  'software_type': 'fooé',
  'parameter': {'param1é': 'value1é', 'param2é': 'value2é'},
  'sla': {'param3': 'value3é', 'param4é': 'value4é'},
  'slave': False,
  'status': 'started',
              }))
  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/json"')
  @changeSkin('Hal')
  def test_requestHateoasHostingSubscription_result(self):
    person_user = self._makePerson()
    fake_request = do_fake_request("POST")
    result = person_user.Person_requestHateoasHostingSubscription(
      REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 201)
    self.assertEquals(result, "")
    # XXX Test that person.request is called.

class TestSlapOSPerson_getHateoasHostingSubscriptionList(TestSlapOSHypermediaMixin):

  @changeSkin('Hal')
  def test_getHateoasHostingSubscriptionList_REQUEST_mandatory(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Person_getHateoasHostingSubscriptionList
    )

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/vnd+bar"')
  @changeSkin('Hal')
  def test_getHateoasHostingSubscriptionList_wrong_ACCEPT(self):
    person_user = self._makePerson()
    fake_request = do_fake_request("GET")
    result = person_user.Person_getHateoasHostingSubscriptionList(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 406)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json')
  @changeSkin('Hal')
  def test_getHateoasHostingSubscriptionList_bad_method(self):
    fake_request = do_fake_request("POST")
    result = self.portal.Person_getHateoasHostingSubscriptionList(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 405)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoasHostingSubscriptionList_not_person_context(self):
    fake_request = do_fake_request("GET")
    result = self.portal.Person_getHateoasHostingSubscriptionList(
      REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 403)
    self.assertEquals(result, "")

  @simulate('Base_getRequestUrl', '*args, **kwargs',
      'return "http://example.org/foo"')
  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  def test_getHateoasHostingSubscriptionList_person_result(self):
    person_user = self._makePerson()
    hosting_subscription = self._makeHostingSubscription()
    hosting_subscription.edit(destination_section_value=person_user)
    self.tic()

    self.login(person_user.getReference())
    self.changeSkin('Hal')
    fake_request = do_fake_request("GET")
    result = person_user.Person_getHateoasHostingSubscriptionList(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/hal+json"
    )
    self.assertEquals(result, json.dumps({
      '_links': {
        "self": {
          "href": "http://example.org/foo",
        },
        "index": {
          "href": "urn:jio:get:%s/ERP5Document_getHateoas" % person_user.getRelativeUrl(),
          "title": "Person"
        },
        "content": [{
          "href": "%s/ERP5Document_getHateoas" % \
              hosting_subscription.absolute_url(),
          "title": "Template Hosting Subscription"
        }],
      },
    }, indent=2))

class TestSlapOSHostingSubscription_getHateoasInstanceList(TestSlapOSHypermediaMixin):

  @changeSkin('Hal')
  def test_getHateoasInstanceList_REQUEST_mandatory(self):
    self.assertRaises(
      Unauthorized,
      self.portal.HostingSubscription_getHateoasInstanceList
    )

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/vnd+bar"')
  @changeSkin('Hal')
  def test_getHateoasInstanceList_wrong_ACCEPT(self):
    subscription = self._makeHostingSubscription()
    fake_request = do_fake_request("GET")
    result = subscription.HostingSubscription_getHateoasInstanceList(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 406)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoasInstanceList_bad_method(self):
    fake_request = do_fake_request("POST")
    result = self.portal.HostingSubscription_getHateoasInstanceList(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 405)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoasInstanceList_not_hosting_subscription_context(self):
    fake_request = do_fake_request("GET")
    result = self.portal.HostingSubscription_getHateoasInstanceList(
      REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 403)
    self.assertEquals(result, "")

  @simulate('Base_getRequestUrl', '*args, **kwargs',
      'return "http://example.org/bar"')
  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoasInstanceList_person_result(self):
    subscription = self._makeHostingSubscription()
    instance= self._makeInstance()
    instance.edit(specialise_value=subscription)
    self.tic()

    fake_request = do_fake_request("GET")
    result = subscription.HostingSubscription_getHateoasInstanceList(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/hal+json"
    )
    self.assertEquals(result, json.dumps({
      '_links': {
        "self": {
          "href": "http://example.org/bar"
        },
        "content": [{
          "href": "%s/ERP5Document_getHateoas" % \
              instance.absolute_url(),
          "title": "Template Software Instance"
        }],
        "index": {
          "href": "urn:jio:get:%s/ERP5Document_getHateoas" % subscription.getRelativeUrl(),
          "title": "Hosting Subscription"
        },
      },
    }, indent=2))

class TestSlapOSHostingSubscription_getHateoasRootSoftwareInstance(TestSlapOSHypermediaMixin):

  @changeSkin('Hal')
  def test_getHateoasRootSoftwareInstance_REQUEST_mandatory(self):
    self.assertRaises(
      Unauthorized,
      self.portal.HostingSubscription_getHateoasRootSoftwareInstance
    )

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/vnd+bar"')
  @changeSkin('Hal')
  def test_getHateoasRootSoftwareInstance_wrong_ACCEPT(self):
    subscription = self._makeHostingSubscription()
    fake_request = do_fake_request("GET")
    result = subscription.HostingSubscription_getHateoasRootSoftwareInstance(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 406)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoasRootSoftwareInstance_bad_method(self):
    fake_request = do_fake_request("POST")
    result = self.portal.HostingSubscription_getHateoasRootSoftwareInstance(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 405)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoasRootSoftwareInstance_not_hosting_subscription_context(self):
    fake_request = do_fake_request("GET")
    result = self.portal.HostingSubscription_getHateoasRootSoftwareInstance(
      REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 403)
    self.assertEquals(result, "")

  @simulate('Base_getRequestUrl', '*args, **kwargs',
      'return "http://example.org/bar"')

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoasRootSoftwareInstance_person_result(self):
    subscription = self._makeHostingSubscription()
    instance = self._makeInstance()
    instance.edit(specialise_value=subscription, title=subscription.getTitle())
    subscription.edit(predecessor_value=instance)
    self.tic()

    fake_request = do_fake_request("GET")
    result = subscription.HostingSubscription_getHateoasRootSoftwareInstance(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/hal+json"
    )
    self.assertEquals(result, json.dumps({
      '_links': {
        "self": {
          "href": "http://example.org/bar"
        },
        "content": [{
          "href": "%s/ERP5Document_getHateoas" % \
              instance.absolute_url(),
        }],
        "index": {
          "href": "urn:jio:get:%s/ERP5Document_getHateoas" % subscription.getRelativeUrl(),
          "title": "Hosting Subscription"
        },
      },
    }, indent=2))

class TestSlapOSInstance_getHateoasNews(TestSlapOSHypermediaMixin):

  def _makeInstance(self):
    instance = self.portal.software_instance_module\
        .template_software_instance.Base_createCloneDocument(batch_mode=1)
    instance.edit(
        title=self.generateNewSoftwareTitle(),
        reference="TESTHS-%s" % self.generateNewId(),
        software_type=self.generateNewSoftwareType(),
        url_string=self.generateNewSoftwareReleaseUrl(),
        instance_xml=self.generateSafeXml(),
        sla_xml=self.generateSafeXml(),
        connection_xml=self.generateSafeXml(),
    )
    self.tic()
    return instance

  @changeSkin('Hal')
  def test_getHateoasNewsInstance_REQUEST_mandatory(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Instance_getHateoasNews
    )

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/vnd+bar"')
  @changeSkin('Hal')
  def test_getHateoasNewsInstance_wrong_ACCEPT(self):
    instance = self._makeInstance()
    fake_request = do_fake_request("GET")
    result = instance.Instance_getHateoasNews(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 406)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoasNewsInstance_bad_method(self):
    instance = self._makeInstance()
    fake_request = do_fake_request("POST")
    result = instance.Instance_getHateoasNews(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 405)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoasNewsInstance_not_instance_context(self):
    fake_request = do_fake_request("GET")
    result = self.portal.Instance_getHateoasNews(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 403)
    self.assertEquals(result, "")

  @simulate('Base_getRequestUrl', '*args, **kwargs',
      'return "http://example.org/bar"')
  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoasNewsInstance_result(self):
    instance = self._makeInstance()
    fake_request = do_fake_request("GET")
    result = instance.Instance_getHateoasNews(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/hal+json"
    )

    self.assertEquals(json.loads(result), json.loads(json.dumps({
      'news': [{
        "user": "SlapOS Master",
        "text": "#error no data found for %s" % instance.getReference()
      }],
      '_links': {
        "self": {
          "href": "http://example.org/bar"
        },
        "index": {
          "href": "urn:jio:get:%s/ERP5Document_getHateoas" % \
            instance.getRelativeUrl(),
          "title": "Software Instance"
        },
      },
    }, indent=2)))


class TestSlapOSInstance_getHateoasInformation(TestSlapOSHypermediaMixin):

  def _makeInstance(self):
    instance = self.portal.software_instance_module\
        .template_software_instance.Base_createCloneDocument(batch_mode=1)
    instance.edit(
        title=self.generateNewSoftwareTitle(),
        reference="TESTHS-%s" % self.generateNewId(),
        software_type=self.generateNewSoftwareType(),
        url_string=self.generateNewSoftwareReleaseUrl(),
        instance_xml=self.generateSafeXml(),
        sla_xml=self.generateSafeXml(),
        connection_xml=self.generateSafeXml(),
    )
    self.tic()
    return instance

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/vnd+bar"')
  @changeSkin('Hal')
  def test_getHateoas_wrong_ACCEPT(self):
    fake_request = do_fake_request("GET")
    result = self.portal.Instance_getHateoasInformation(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 406)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoas_bad_method(self):
    fake_request = do_fake_request("POST")
    result = self.portal.Instance_getHateoasInformation(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 405)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoas_request_not_correct_context(self):
    fake_request = do_fake_request("GET")
    result = self.portal.Instance_getHateoasInformation(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 403)
    self.assertEquals(result, "")

  @simulate('Base_getRequestUrl', '*args, **kwargs',
      'return "http://example.org/foo"')
  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoas_result(self):
    instance = self._makeInstance()
    instance.edit(url_string="http://foo.com/software.cfg")
    self.portal.portal_workflow._jumpToStateFor(instance,
        'start_requested')
    fake_request = do_fake_request("GET")
    result = instance.Instance_getHateoasInformation(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/hal+json"
    )
    self.assertEquals(json.loads(result), json.loads(json.dumps({
      'title': instance.getTitle(),
      'requested_state': 'started',
      'slave': False,
      'instance_guid': instance.getId(),
      'connection_dict': instance.getConnectionXmlAsDict(),
      'parameter_dict': instance.getInstanceXmlAsDict(),
      'software_type': instance.getSourceReference(),
      'sla_dict': instance.getSlaXmlAsDict(),
      '_links': {
        "self": {
          "href": "http://example.org/foo"
        },
        "software_release": {
          "href": "http://foo.com/software.cfg",
        },
        "index": {
          "href": "urn:jio:get:%s/ERP5Document_getHateoas" % instance.getRelativeUrl(),
          "title": "Software Instance"
        },
      },
    }, indent=2)))

class TestSlapOSPerson_getHateoasComputerList(TestSlapOSHypermediaMixin):

  @changeSkin('Hal')
  def test_getHateoasComputerList_REQUEST_mandatory(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Person_getHateoasComputerList
    )

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/vnd+bar"')
  @changeSkin('Hal')
  def test_getHateoasComputerList_wrong_ACCEPT(self):
    fake_request = do_fake_request("GET")
    result = self.portal.Person_getHateoasComputerList(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 406)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoasComputerList_bad_method(self):
    fake_request = do_fake_request("POST")
    result = self.portal.Person_getHateoasComputerList(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 405)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoasComputerList_request_not_correct_context(self):
    fake_request = do_fake_request("GET")
    result = self.portal.Person_getHateoasComputerList(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 403)
    self.assertEquals(result, "")

  @simulate('Base_getRequestUrl', '*args, **kwargs',
      'return "http://example.org/foo"')
  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoasComputerList_result(self):
    person_user = self._makePerson()
    computer = self._makeComputer()
    computer.edit(source_administration_value=person_user)
    self.tic()
    fake_request = do_fake_request("GET")
    self.changeSkin('Hal')
    result = person_user.Person_getHateoasComputerList(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/hal+json"
    )
    self.assertEquals(json.loads(result), json.loads(json.dumps({
      '_links': {
        "self": {
          "href": "http://example.org/foo"
        },
        "index": {
          "href": "urn:jio:get:%s/ERP5Document_getHateoas" % \
            person_user.getRelativeUrl(),
          "title": "Person"
        },
        "content": [{
          "href": "%s/ERP5Document_getHateoas" % \
              computer.absolute_url(),
          "title": computer.getTitle()
        }],
      },
    }, indent=2)))

class TestSlapOSComputer_getHateoasSoftwareInstallationList(TestSlapOSHypermediaMixin):

  @changeSkin('Hal')
  def test_getSoftwareInstallationList_REQUEST_mandatory(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Computer_getHateoasSoftwareInstallationList
    )

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/vnd+bar"')
  @changeSkin('Hal')
  def test_getSoftwareInstallationList_wrong_ACCEPT(self):
    fake_request = do_fake_request("GET")
    result = self.portal.Computer_getHateoasSoftwareInstallationList(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 406)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getSoftwareInstallationList_bad_method(self):
    fake_request = do_fake_request("POST")
    result = self.portal.Computer_getHateoasSoftwareInstallationList(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 405)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getSoftwareInstallationList_request_not_correct_context(self):
    fake_request = do_fake_request("GET")
    result = self.portal.Computer_getHateoasSoftwareInstallationList(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 403)
    self.assertEquals(result, "")

  @simulate('Base_getRequestUrl', '*args, **kwargs',
      'return "http://example.org/foo"')
  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getSoftwareInstallationList_result(self):
    computer = self._makeComputer()
    software_installation = self._makeSoftwareInstallation()
    software_installation.edit(aggregate_value=computer, url_string='foo')
    self.tic()
    fake_request = do_fake_request("GET")
    result = computer.Computer_getHateoasSoftwareInstallationList(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/hal+json"
    )
    self.assertEquals(json.loads(result), json.loads(json.dumps({
      '_links': {
        "self": {
          "href": "http://example.org/foo"
        },
        "content": [{
          "href": "%s/ERP5Document_getHateoas" % \
              software_installation.absolute_url(),
          "title": "foo"
        }],
        "index": {
          "href": "urn:jio:get:%s/ERP5Document_getHateoas" % computer.getRelativeUrl(),
          "title": "Computer"
        },
      },
    }, indent=2)))

class TestSlapOSSoftwareInstallation_getHateoasInformation(TestSlapOSHypermediaMixin):

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/vnd+bar"')
  @changeSkin('Hal')
  def test_getHateoas_wrong_ACCEPT(self):
    fake_request = do_fake_request("GET")
    result = self.portal.SoftwareInstallation_getHateoasInformation(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 406)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoas_bad_method(self):
    fake_request = do_fake_request("POST")
    result = self.portal.SoftwareInstallation_getHateoasInformation(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 405)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoas_request_not_correct_context(self):
    fake_request = do_fake_request("GET")
    result = self.portal.SoftwareInstallation_getHateoasInformation(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 403)
    self.assertEquals(result, "")

  @simulate('Base_getRequestUrl', '*args, **kwargs',
      'return "http://example.org/foo"')
  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoas_result(self):
    software_installation = self._makeSoftwareInstallation()
    software_installation.edit(url_string="http://foo.com/software.cfg")
    self.portal.portal_workflow._jumpToStateFor(software_installation,
        'start_requested')
    fake_request = do_fake_request("GET")
    result = software_installation.SoftwareInstallation_getHateoasInformation(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/hal+json"
    )
    self.assertEquals(json.loads(result), json.loads(json.dumps({
      'title': software_installation.getTitle(),
      'status': 'started',
      '_links': {
        "self": {
          "href": "http://example.org/foo"
        },
        "software_release": {
          "href": "http://foo.com/software.cfg",
        },
        "index": {
          "href": "urn:jio:get:%s/ERP5Document_getHateoas" % software_installation.getRelativeUrl(),
          "title": "Software Installation"
        },
      },
    }, indent=2)))
