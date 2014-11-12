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

class TestSlapOSBase_getRequestHeader(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

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

class TestSlapOSBase_getRequestUrl(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def test_getRequestUrl_REQUEST_disallowed(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Base_getRequestUrl,
      REQUEST={})

  @skip('TODO')
  def test_getRequestUrl_matching_key(self):
    pass

class TestSlapOSBase_getRequestBody(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def test_getRequestBody_REQUEST_disallowed(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Base_getRequestBody,
      REQUEST={})

  @skip('TODO')
  def test_getRequestBody_matching_key(self):
    pass

class TestSlapOSBase_handleAcceptHeader(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def test_handleAcceptHeader_REQUEST_disallowed(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Base_handleAcceptHeader,
      [],
      REQUEST={})

  @simulate('Base_getRequestHeader', '*args, **kwargs', 'return "*/*"')
  def test_handleAcceptHeader_star_accept(self):
    self.assertEquals(
        self.portal.Base_handleAcceptHeader(['application/vnd+test',
                                             'application/vnd+test2']),
        'application/vnd+test'
        )

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd+2test"')
  def test_handleAcceptHeader_matching_type(self):
    self.assertEquals(
        self.portal.Base_handleAcceptHeader(['application/vnd+test',
                                             'application/vnd+2test']),
        'application/vnd+2test'
        )

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd+2test"')
  def test_handleAcceptHeader_non_matching_type(self):
    self.assertEquals(
        self.portal.Base_handleAcceptHeader(['application/vnd+test']),
        None
        )

class TestSlapOSBase_getHateoasMaster(testSlapOSMixin):

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
    return person_user

  def beforeTearDown(self):
    transaction.abort()

  def test_getHateoasMaster_REQUEST_mandatory(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Base_getHateoasMaster
    )

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd+bar"')
  def test_getHateoasMaster_wrong_ACCEPT(self):
    fake_request = do_fake_request("GET")
    result = self.portal.Base_getHateoasMaster(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 406)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.master"')
  def test_getHateoasMaster_bad_method(self):
    fake_request = do_fake_request("POST")
    result = self.portal.Base_getHateoasMaster(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 405)
    self.assertEquals(result, "")

  @simulate('Base_getRequestUrl', '*args, **kwargs', 
      'return "http://example.org/bar"')
  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.master"')
  def test_getHateoasMaster_anonymous_result(self):
    self.logout()
    fake_request = do_fake_request("GET")
    result = self.portal.Base_getHateoasMaster(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/vnd.slapos.org.hal+json; class=slapos.org.master"
    )
    self.assertEquals(result, json.dumps({
      '_class': 'slapos.org.master',
      '_links': {
        "self": {
          "href": "http://example.org/bar",
          "type": "application/vnd.slapos.org.hal+json; class=slapos.org.master"
        },
      },
    }))

  @simulate('Base_getRequestUrl', '*args, **kwargs', 
      'return "http://example.org/bar"')
  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.master"')
  def test_getHateoasMaster_person_result(self):
    person_user = self._makePerson()
    self.login(person_user.getReference())
    fake_request = do_fake_request("GET")
    result = self.portal.Base_getHateoasMaster(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/vnd.slapos.org.hal+json; class=slapos.org.master"
    )
    self.assertEquals(result, json.dumps({
      '_class': 'slapos.org.master',
      '_links': {
        "self": {
          "href": "http://example.org/bar",
          "type": "application/vnd.slapos.org.hal+json; class=slapos.org.master"
        },
        "http://slapos.org/reg/me": {
          "href": "%s/Person_getHateoas" % person_user.absolute_url(),
          "type": "application/vnd.slapos.org.hal+json; class=slapos.org.person"
        },
      },
    }))

class TestSlapOSPerson_getHateoas(testSlapOSMixin):

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
    return person_user

  def beforeTearDown(self):
    transaction.abort()

  def test_getHateoasPerson_REQUEST_mandatory(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Person_getHateoas
    )

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd+bar"')
  def test_getHateoasPerson_wrong_ACCEPT(self):
    person_user = self._makePerson()
    fake_request = do_fake_request("GET")
    result = person_user.Person_getHateoas(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 406)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.person"')
  def test_getHateoasPerson_bad_method(self):
    person_user = self._makePerson()
    fake_request = do_fake_request("POST")
    result = person_user.Person_getHateoas(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 405)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.person"')
  def test_getHateoasPerson_not_person_context(self):
    fake_request = do_fake_request("GET")
    result = self.portal.Person_getHateoas(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 403)
    self.assertEquals(result, "")

  @simulate('Base_getRequestUrl', '*args, **kwargs', 
      'return "http://example.org/bar"')
  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.person"')
  def test_getHateoasPerson_result(self):
    person_user = self._makePerson()
    fake_request = do_fake_request("GET")
    result = person_user.Person_getHateoas(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/vnd.slapos.org.hal+json; class=slapos.org.person"
    )
    self.assertEquals(result, json.dumps({
      '_class': 'slapos.org.person',
      'title': person_user.getTitle(),
      '_links': {
        "self": {
          "href": "http://example.org/bar",
          "type": "application/vnd.slapos.org.hal+json; class=slapos.org.person"
        },
        "http://slapos.org/reg/request": {
          "href": "%s/Person_requestHateoasHostingSubscription" % \
            person_user.absolute_url(),
          "method": "POST",
          "type": "application/json; class=slapos.org.hosting_subscription",
        },
        "http://slapos.org/reg/computer": {
          "href": "%s/Person_getHateoasComputerList" % \
            person_user.absolute_url(),
          "type": "application/vnd.slapos.org.hal+json; " \
                  "class=slapos.org.collection",
        },
        "http://slapos.org/reg/hosting_subscription": {
          "href": "%s/Person_getHateoasHostingSubscriptionList" % \
            person_user.absolute_url(),
          "type": "application/vnd.slapos.org.hal+json; " \
                  "class=slapos.org.collection"
        },
      },
    }))


class TestSlapOSPerson_requestHateoasHostingSubscription(testSlapOSMixin):

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
    return person_user

  def beforeTearDown(self):
    transaction.abort()

  def test_requestHateoasHostingSubscription_REQUEST_mandatory(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Person_requestHateoasHostingSubscription
    )

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd+bar"')
  def test_requestHateoasHostingSubscription_wrong_CONTENT(self):
    person_user = self._makePerson()
    fake_request = do_fake_request("POST")
    result = person_user.Person_requestHateoasHostingSubscription(
      REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 406)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/json; ' \
                    'class=slapos.org.hosting_subscription"')
  def test_requestHateoasHostingSubscription_bad_method(self):
    person_user = self._makePerson()
    fake_request = do_fake_request("GET")
    result = person_user.Person_requestHateoasHostingSubscription(
      REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 405)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/json; ' \
                    'class=slapos.org.hosting_subscription"')
  def test_requestHateoasHostingSubscription_not_person_context(self):
    fake_request = do_fake_request("POST")
    result = self.portal.Person_requestHateoasHostingSubscription(
      REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 403)
    self.assertEquals(result, "")

  @simulate('Base_getRequestBody', '*args, **kwargs', 
            'return "[}"')
  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/json; ' \
                    'class=slapos.org.hosting_subscription"')
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
            'return "application/json; ' \
                    'class=slapos.org.hosting_subscription"')
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
            'return "application/json; ' \
                    'class=slapos.org.hosting_subscription"')
  def test_requestHateoasHostingSubscription_result(self):
    person_user = self._makePerson()
    fake_request = do_fake_request("POST")
    result = person_user.Person_requestHateoasHostingSubscription(
      REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 201)
    self.assertEquals(result, "")
    # XXX Test that person.request is called.

class TestSlapOSPerson_getHateoasHostingSubscriptionList(testSlapOSMixin):

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
    return person_user

  def _makeHostingSubscription(self):
    hosting_subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    hosting_subscription.validate()
#     hosting_subscription.edit(
#         title=self.generateNewSoftwareTitle(),
#         reference="TESTHS-%s" % self.generateNewId(),
#     )
#     self.request_kw = dict(
#       software_release=\
#           self.generateNewSoftwareReleaseUrl(),
#       software_type=self.generateNewSoftwareType(),
#       instance_xml=self.generateSafeXml(),
#       sla_xml=self.generateSafeXml(),
#       shared=False,
#       software_title=hosting_subscription.getTitle(),
#       state='started'
#     )
#     hosting_subscription.requestStart(**self.request_kw)
#     hosting_subscription.requestInstance(**self.request_kw)
    self.tic()
    return hosting_subscription

  def beforeTearDown(self):
    transaction.abort()

  def test_getHateoasHostingSubscriptionList_REQUEST_mandatory(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Person_getHateoasHostingSubscriptionList
    )

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd+bar"')
  def test_getHateoasHostingSubscriptionList_wrong_ACCEPT(self):
    person_user = self._makePerson()
    fake_request = do_fake_request("GET")
    result = person_user.Person_getHateoasHostingSubscriptionList(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 406)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.collection"')
  def test_getHateoasHostingSubscriptionList_bad_method(self):
    fake_request = do_fake_request("POST")
    result = self.portal.Person_getHateoasHostingSubscriptionList(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 405)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.collection"')
  def test_requestHateoasHostingSubscription_not_person_context(self):
    fake_request = do_fake_request("GET")
    result = self.portal.Person_getHateoasHostingSubscriptionList(
      REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 403)
    self.assertEquals(result, "")

  @simulate('Base_getRequestUrl', '*args, **kwargs', 
      'return "http://example.org/foo"')
  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.collection"')
  def test_getHateoasHostingSubscriptionList_person_result(self):
    person_user = self._makePerson()
    hosting_subscription = self._makeHostingSubscription()
    hosting_subscription.edit(destination_section_value=person_user)
    self.tic()

    self.login(person_user.getReference())
    fake_request = do_fake_request("GET")
    result = person_user.Person_getHateoasHostingSubscriptionList(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/vnd.slapos.org.hal+json; class=slapos.org.collection"
    )
    self.assertEquals(result, json.dumps({
      '_class': 'slapos.org.collection',
      '_links': {
        "self": {
          "href": "http://example.org/foo",
          "type": "application/vnd.slapos.org.hal+json; " \
                  "class=slapos.org.collection"
        },
        "item": [{
          "href": "%s/HostingSubscription_getHateoas" % \
              hosting_subscription.absolute_url(),
          "type": "application/vnd.slapos.org.hal+json; " \
                  "class=slapos.org.hosting_subscription"
        }],
      },
    }))

class TestSlapOSHostingSubscription_getHateoas(testSlapOSMixin):

  def _makeHostingSubscription(self):
    hosting_subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    hosting_subscription.edit(
        title=self.generateNewSoftwareTitle(),
        reference="TESTHS-%s" % self.generateNewId(),
    )
    self.tic()
    return hosting_subscription

  def beforeTearDown(self):
    transaction.abort()

  def test_getHateoasHostingSubscription_REQUEST_mandatory(self):
    self.assertRaises(
      Unauthorized,
      self.portal.HostingSubscription_getHateoas
    )

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd+bar"')
  def test_getHateoasHostingSubscription_wrong_ACCEPT(self):
    hosting_subscription = self._makeHostingSubscription()
    fake_request = do_fake_request("GET")
    result = hosting_subscription.HostingSubscription_getHateoas(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 406)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.hosting_subscription"')
  def test_getHateoasHostingSubscription_bad_method(self):
    hosting_subscription = self._makeHostingSubscription()
    fake_request = do_fake_request("POST")
    result = hosting_subscription.HostingSubscription_getHateoas(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 405)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.hosting_subscription"')
  def test_getHateoasHostingSubscription_not_hosting_subscription_context(self):
    fake_request = do_fake_request("GET")
    result = self.portal.HostingSubscription_getHateoas(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 403)
    self.assertEquals(result, "")

  @simulate('Base_getRequestUrl', '*args, **kwargs', 
      'return "http://example.org/bar"')
  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.hosting_subscription"')
  def test_getHateoasHostingSubscription_result(self):
    hosting_subscription = self._makeHostingSubscription()
    fake_request = do_fake_request("GET")
    result = hosting_subscription.HostingSubscription_getHateoas(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/vnd.slapos.org.hal+json; class=slapos.org.hosting_subscription"
    )
    self.assertEquals(result, json.dumps({
      '_class': 'slapos.org.hosting_subscription',
      'title': hosting_subscription.getTitle(),
      '_links': {
        "self": {
          "href": "http://example.org/bar",
          "type": "application/vnd.slapos.org.hal+json; " \
                  "class=slapos.org.hosting_subscription"
        },
        "http://slapos.org/reg/instance": {
          "href": "%s/HostingSubscription_getHateoasInstanceList" % \
            hosting_subscription.absolute_url(),
          "type": "application/vnd.slapos.org.hal+json; " \
                  "class=slapos.org.collection"
        },
      },
    }))

class TestSlapOSHostingSubscription_getHateoasInstanceList(testSlapOSMixin):

  def _makeHostingSubscription(self):
    hosting_subscription = self.portal.hosting_subscription_module\
        .template_hosting_subscription.Base_createCloneDocument(batch_mode=1)
    hosting_subscription.validate()
    self.tic()
    return hosting_subscription

  def _makeInstance(self):
    instance = self.portal.software_instance_module\
        .template_software_instance.Base_createCloneDocument(batch_mode=1)
    instance.validate()
    self.tic()
    return instance

  def beforeTearDown(self):
    transaction.abort()

  def test_getHateoasInstanceList_REQUEST_mandatory(self):
    self.assertRaises(
      Unauthorized,
      self.portal.HostingSubscription_getHateoasInstanceList
    )

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd+bar"')
  def test_getHateoasInstanceList_wrong_ACCEPT(self):
    subscription = self._makeHostingSubscription()
    fake_request = do_fake_request("GET")
    result = subscription.HostingSubscription_getHateoasInstanceList(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 406)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.collection"')
  def test_getHateoasInstanceList_bad_method(self):
    fake_request = do_fake_request("POST")
    result = self.portal.HostingSubscription_getHateoasInstanceList(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 405)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.collection"')
  def test_requestHateoasHostingSubscription_not_person_context(self):
    fake_request = do_fake_request("GET")
    result = self.portal.HostingSubscription_getHateoasInstanceList(
      REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 403)
    self.assertEquals(result, "")

  @simulate('Base_getRequestUrl', '*args, **kwargs', 
      'return "http://example.org/bar"')
  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.collection"')
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
      "application/vnd.slapos.org.hal+json; class=slapos.org.collection"
    )
    self.assertEquals(result, json.dumps({
      '_class': 'slapos.org.collection',
      '_links': {
        "self": {
          "href": "http://example.org/bar",
          "type": "application/vnd.slapos.org.hal+json; " \
                  "class=slapos.org.collection"
        },
        "item": [{
          "href": "%s/Instance_getHateoas" % \
              instance.absolute_url(),
          "type": "application/vnd.slapos.org.hal+json; " \
                  "class=slapos.org.instance"
        }],
      },
    }))

class TestSlapOSInstance_getHateoas(testSlapOSMixin):

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

  def beforeTearDown(self):
    transaction.abort()

  def test_getHateoasInstance_REQUEST_mandatory(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Instance_getHateoas
    )

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd+bar"')
  def test_getHateoasInstance_wrong_ACCEPT(self):
    instance = self._makeInstance()
    fake_request = do_fake_request("GET")
    result = instance.Instance_getHateoas(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 406)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.instance"')
  def test_getHateoasInstance_bad_method(self):
    instance = self._makeInstance()
    fake_request = do_fake_request("POST")
    result = instance.Instance_getHateoas(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 405)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.instance"')
  def test_getHateoasInstance_not_instance_context(self):
    fake_request = do_fake_request("GET")
    result = self.portal.Instance_getHateoas(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 403)
    self.assertEquals(result, "")

  @simulate('Base_getRequestUrl', '*args, **kwargs', 
      'return "http://example.org/bar"')
  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.instance"')
  def test_getHateoasInstance_result(self):
    instance = self._makeInstance()
    fake_request = do_fake_request("GET")
    result = instance.Instance_getHateoas(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/vnd.slapos.org.hal+json; class=slapos.org.instance"
    )

    self.assertEquals(json.loads(result), json.loads(json.dumps({
      '_class': 'slapos.org.instance',
      'title': instance.getTitle(),
      'slave': False,
      'software_type': instance.getSourceReference(),
      'parameter': instance.getInstanceXmlAsDict(),
      'sla': instance.getSlaXmlAsDict(),
      'connection': instance.getConnectionXmlAsDict(),
      'status': 'destroyed',
      '_links': {
        "self": {
          "href": "http://example.org/bar",
          "type": "application/vnd.slapos.org.hal+json; " \
                  "class=slapos.org.instance"
        },
        "http://slapos.org/reg/news": {
          "href": "%s/Instance_getHateoasNews" % instance.absolute_url(),
          "type": "application/vnd.slapos.org.hal+json; " \
                  "class=slapos.org.news"
        },
        "http://slapos.org/reg/release": {
          "href": instance.getUrlString(),
        },
      },
    })))

class TestSlapOSInstance_getHateoasNews(testSlapOSMixin):

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

  def beforeTearDown(self):
    transaction.abort()

  def test_getHateoasNewsInstance_REQUEST_mandatory(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Instance_getHateoasNews
    )

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd+bar"')
  def test_getHateoasNewsInstance_wrong_ACCEPT(self):
    instance = self._makeInstance()
    fake_request = do_fake_request("GET")
    result = instance.Instance_getHateoasNews(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 406)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.news"')
  def test_getHateoasNewsInstance_bad_method(self):
    instance = self._makeInstance()
    fake_request = do_fake_request("POST")
    result = instance.Instance_getHateoasNews(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 405)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.news"')
  def test_getHateoasNewsInstance_not_instance_context(self):
    fake_request = do_fake_request("GET")
    result = self.portal.Instance_getHateoasNews(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 403)
    self.assertEquals(result, "")

  @simulate('Base_getRequestUrl', '*args, **kwargs', 
      'return "http://example.org/bar"')
  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.news"')
  def test_getHateoasNewsInstance_result(self):
    instance = self._makeInstance()
    fake_request = do_fake_request("GET")
    result = instance.Instance_getHateoasNews(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/vnd.slapos.org.hal+json; class=slapos.org.news"
    )

    self.assertEquals(json.loads(result), json.loads(json.dumps({
      '_class': 'slapos.org.news',
      'news': [{
        "user": "SlapOS Master",
        "text": "#error no data found for %s" % instance.getReference()
      }],
      '_links': {
        "self": {
          "href": "http://example.org/bar",
          "type": "application/vnd.slapos.org.hal+json; " \
                  "class=slapos.org.news"
        },
        "http://slapos.org/reg/instance": {
          "href": "%s/Instance_getHateoas" % instance.absolute_url(),
          "type": "application/vnd.slapos.org.hal+json; " \
                  "class=slapos.org.instance"
        },
      },
    })))

class TestSlapOSPerson_getHateoasComputerList(testSlapOSMixin):

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
    return person_user

  def _makeComputer(self):
    computer = self.portal.computer_module\
        .template_computer.Base_createCloneDocument(batch_mode=1)
    computer.validate()
    return computer

  def test_getHateoasComputerList_REQUEST_mandatory(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Person_getHateoasComputerList
    )

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd+bar"')
  def test_getHateoasComputerList_wrong_ACCEPT(self):
    fake_request = do_fake_request("GET")
    result = self.portal.Person_getHateoasComputerList(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 406)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                  'class=slapos.org.collection"')
  def test_getHateoasComputerList_bad_method(self):
    fake_request = do_fake_request("POST")
    result = self.portal.Person_getHateoasComputerList(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 405)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                  'class=slapos.org.collection"')
  def test_getHateoasComputerList_request_not_correct_context(self):
    fake_request = do_fake_request("GET")
    result = self.portal.Person_getHateoasComputerList(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 403)
    self.assertEquals(result, "")

  @simulate('Base_getRequestUrl', '*args, **kwargs', 
      'return "http://example.org/foo"')
  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.collection"')
  def test_getHateoasComputerList_result(self):
    person_user = self._makePerson()
    computer = self._makeComputer()
    computer.edit(source_administration_value=person_user)
    self.tic()
    fake_request = do_fake_request("GET")
    result = person_user.Person_getHateoasComputerList(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/vnd.slapos.org.hal+json; class=slapos.org.collection"
    )
    self.assertEquals(json.loads(result), json.loads(json.dumps({
      '_class': 'slapos.org.collection',
      '_links': {
        "self": {
          "href": "http://example.org/foo",
          "type": "application/vnd.slapos.org.hal+json; " \
                  "class=slapos.org.collection"
        },
        "item": [{
          "href": "%s/Computer_getHateoas" % \
              computer.absolute_url(),
          "type": "application/vnd.slapos.org.hal+json; " \
                  "class=slapos.org.computer"
        }],
      },
    })))

class TestSlapOSComputer_getHateoas(testSlapOSMixin):

  def _makeComputer(self):
    computer = self.portal.computer_module\
        .template_computer.Base_createCloneDocument(batch_mode=1)
    computer.validate()
    self.tic()
    return computer

  def test_getHateoasComputerList_REQUEST_mandatory(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Computer_getHateoas
    )

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd+bar"')
  def test_getHateoas_wrong_ACCEPT(self):
    fake_request = do_fake_request("GET")
    result = self.portal.Computer_getHateoas(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 406)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                  'class=slapos.org.computer"')
  def test_getHateoas_bad_method(self):
    fake_request = do_fake_request("POST")
    result = self.portal.Computer_getHateoas(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 405)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                  'class=slapos.org.computer"')
  def test_getHateoas_request_not_correct_context(self):
    fake_request = do_fake_request("GET")
    result = self.portal.Computer_getHateoas(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 403)
    self.assertEquals(result, "")

  @simulate('Base_getRequestUrl', '*args, **kwargs', 
      'return "http://example.org/foo"')
  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.computer"')
  def test_getHateoas_result(self):
    computer = self._makeComputer()
    fake_request = do_fake_request("GET")
    result = computer.Computer_getHateoas(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/vnd.slapos.org.hal+json; class=slapos.org.computer"
    )
    self.assertEquals(json.loads(result), json.loads(json.dumps({
      '_class': 'slapos.org.computer',
      'title': computer.getTitle(),
      '_links': {
        "self": {
          "href": "http://example.org/foo",
          "type": "application/vnd.slapos.org.hal+json; " \
                  "class=slapos.org.computer"
        },
        "http://slapos.org/reg/software": {
          "href": "%s/Computer_getHateoasSoftwareInstallationList" % \
              computer.absolute_url(),
          "type": "application/vnd.slapos.org.hal+json; " \
                  "class=slapos.org.collection"
        },
      },
    })))

class TestSlapOSComputer_getHateoasSoftwareInstallationList(testSlapOSMixin):

  def _makeComputer(self):
    computer = self.portal.computer_module\
        .template_computer.Base_createCloneDocument(batch_mode=1)
    computer.validate()
    return computer

  def _makeSoftwareInstallation(self):
    software_installation = self.portal.software_installation_module\
        .template_software_installation.Base_createCloneDocument(batch_mode=1)
    software_installation.validate()
    return software_installation

  def test_getSoftwareInstallationList_REQUEST_mandatory(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Computer_getHateoasSoftwareInstallationList
    )

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd+bar"')
  def test_getSoftwareInstallationList_wrong_ACCEPT(self):
    fake_request = do_fake_request("GET")
    result = self.portal.Computer_getHateoasSoftwareInstallationList(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 406)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                  'class=slapos.org.collection"')
  def test_getSoftwareInstallationList_bad_method(self):
    fake_request = do_fake_request("POST")
    result = self.portal.Computer_getHateoasSoftwareInstallationList(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 405)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                  'class=slapos.org.collection"')
  def test_getSoftwareInstallationList_request_not_correct_context(self):
    fake_request = do_fake_request("GET")
    result = self.portal.Computer_getHateoasSoftwareInstallationList(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 403)
    self.assertEquals(result, "")

  @simulate('Base_getRequestUrl', '*args, **kwargs', 
      'return "http://example.org/foo"')
  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.collection"')
  def test_getSoftwareInstallationList_result(self):
    computer = self._makeComputer()
    software_installation = self._makeSoftwareInstallation()
    software_installation.edit(aggregate_value=computer)
    self.tic()
    fake_request = do_fake_request("GET")
    result = computer.Computer_getHateoasSoftwareInstallationList(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/vnd.slapos.org.hal+json; class=slapos.org.collection"
    )
    self.assertEquals(json.loads(result), json.loads(json.dumps({
      '_class': 'slapos.org.collection',
      '_links': {
        "self": {
          "href": "http://example.org/foo",
          "type": "application/vnd.slapos.org.hal+json; " \
                  "class=slapos.org.collection"
        },
        "item": [{
          "href": "%s/SoftwareInstallation_getHateoas" % \
              software_installation.absolute_url(),
          "type": "application/vnd.slapos.org.hal+json; " \
                  "class=slapos.org.software_installation"
        }],
      },
    })))

class TestSlapOSSoftwareInstallation_getHateoas(testSlapOSMixin):

  def _makeSoftwareInstallation(self):
    software_installation = self.portal.software_installation_module\
        .template_software_installation.Base_createCloneDocument(batch_mode=1)
    software_installation.validate()
    return software_installation

  def test_getHateoas_REQUEST_mandatory(self):
    self.assertRaises(
      Unauthorized,
      self.portal.SoftwareInstallation_getHateoas
    )

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd+bar"')
  def test_getHateoas_wrong_ACCEPT(self):
    fake_request = do_fake_request("GET")
    result = self.portal.SoftwareInstallation_getHateoas(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 406)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                  'class=slapos.org.software_installation"')
  def test_getHateoas_bad_method(self):
    fake_request = do_fake_request("POST")
    result = self.portal.SoftwareInstallation_getHateoas(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 405)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                  'class=slapos.org.software_installation"')
  def test_getHateoas_request_not_correct_context(self):
    fake_request = do_fake_request("GET")
    result = self.portal.SoftwareInstallation_getHateoas(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 403)
    self.assertEquals(result, "")

  @simulate('Base_getRequestUrl', '*args, **kwargs', 
      'return "http://example.org/foo"')
  @simulate('Base_getRequestHeader', '*args, **kwargs', 
            'return "application/vnd.slapos.org.hal+json; ' \
                    'class=slapos.org.software_installation"')
  def test_getHateoas_result(self):
    software_installation = self._makeSoftwareInstallation()
    software_installation.edit(url_string="http://foo.com/software.cfg")
    self.portal.portal_workflow._jumpToStateFor(software_installation,
        'start_requested')
    fake_request = do_fake_request("GET")
    result = software_installation.SoftwareInstallation_getHateoas(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/vnd.slapos.org.hal+json; class=slapos.org.software_installation"
    )
    self.assertEquals(json.loads(result), json.loads(json.dumps({
      '_class': 'slapos.org.software_installation',
      'title': software_installation.getTitle(),
      'status': 'started',
      '_links': {
        "self": {
          "href": "http://example.org/foo",
          "type": "application/vnd.slapos.org.hal+json; " \
                  "class=slapos.org.software_installation"
        },
        "software_release": {
          "href": "http://foo.com/software.cfg",
        },
      },
    })))
