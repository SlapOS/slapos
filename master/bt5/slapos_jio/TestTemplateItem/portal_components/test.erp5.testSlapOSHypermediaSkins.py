# -*- coding: utf-8 -*-
# Copyright (c) 2002-2013 Nexedi SA and Contributors. All Rights Reserved.
from erp5.component.test.SlapOSTestCaseMixin import \
  SlapOSTestCaseMixinWithAbort, changeSkin, simulate
from erp5.component.test.testHalJsonStyle import \
  do_fake_request

import json
from zExceptions import Unauthorized

class TestSlapOSHypermediaMixin(SlapOSTestCaseMixinWithAbort):
  def afterSetUp(self):
    SlapOSTestCaseMixinWithAbort.afterSetUp(self)
    self.changeSkin('Hal')

  def _makePerson(self):
    person_user = self.makePerson()
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
        u'href': u'%s/Person_getHateoasComputerList' % \
          person_user.absolute_url(),
        u'name': u'get_hateoas_computer_list',
        u'icon': u'',
        u'title': u'getHateoasComputerList'
      },
      {
        u'href': u'%s/Person_getHateoasHostingSubscriptionList' % \
          person_user.absolute_url(),
        u'name': u'get_hateoas_hosting_subscription_list',
        u'icon': u'',
        u'title': u'getHateoasHostingSubscriptionList'
      },
      {
        u'href': u'%s/Person_getHateoasInformation' % \
          person_user.absolute_url(),
        u'name': u'get_hateoas_information',
        u'icon': u'',
        u'title': u'getHateoasInformation'
      },
    ]:
      self.assertTrue(action in action_object_slap, \
        "%s not in %s" % (action, action_object_slap))
    self.assertEquals(results['_links']['action_object_slap_post'], {
        u"href": u'%s/Person_requestHateoasHostingSubscription' %  \
          person_user.absolute_url(),
        u"name": u"request_hateoas_hosting_subscription",
        u'icon': u'',
        u"title": u"requestHateoasHostingSubscription"
    })



class TestSlapOSERP5Document_getHateoas_me(TestSlapOSHypermediaMixin):
  """
    Complementary tests to ensure "me" is present on the request.
  """

  @simulate('Base_getRequestUrl', '*args, **kwargs',
      'return "http://example.org/bar"')
  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def _test_me(self, me=None):
    self.changeSkin('Hal')
    fake_request = do_fake_request("GET")
    result = self.portal.ERP5Document_getHateoas(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/hal+json"
    )
    result = json.loads(result)
    self.assertEquals(result['_links']['self'],
        {"href": "http://example.org/bar"}
    )
    self.assertEqual(result['_links'].get('me'), me)

  def test_me_annonymous(self):
    self.logout()
    self._test_me()

  def test_me_person(self):
    person_user = self._makePerson()
    self.login(person_user.getUserId())
    self._test_me(
      {"href": "urn:jio:get:%s" % person_user.getRelativeUrl()})

  def test_me_instance(self):
    self._makeTree()
    self.login(self.software_instance.getUserId())
    self._test_me(
      {"href": "urn:jio:get:%s" % self.software_instance.getRelativeUrl()}
    )

  def test_me_computer(self):
    computer = self._makeComputer()
    self.tic()
    self.login(computer.getUserId())
    self._test_me(
      {"href": "urn:jio:get:%s" % computer.getRelativeUrl()}
    )

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

    self.login(person_user.getUserId())
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
          "href": "urn:jio:get:%s" % person_user.getRelativeUrl(),
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
          "href": "urn:jio:get:%s" % subscription.getRelativeUrl(),
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
          "href": "urn:jio:get:%s" % subscription.getRelativeUrl(),
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
    self._addERP5Login(instance)
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
          "href": "urn:jio:get:%s" % \
            instance.getRelativeUrl(),
          "title": "Software Instance"
        },
      },
    }, indent=2)))

class TestSlapOSInstance_getHateoasRelatedHostingSubscription(TestSlapOSHypermediaMixin):

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
    self._addERP5Login(instance)
    self.tic()
    return instance

  @changeSkin('Hal')
  def test_getHateoasRelatedHostingSubscription_REQUEST_mandatory(self):
    self.assertRaises(
      Unauthorized,
      self.portal.Instance_getHateoasRelatedHostingSubscription
    )

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/vnd+bar"')
  @changeSkin('Hal')
  def test_getHateoasRelatedHostingSubscription_wrong_ACCEPT(self):
    instance = self._makeInstance()
    fake_request = do_fake_request("GET")
    result = instance.Instance_getHateoasRelatedHostingSubscription(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 406)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoasRelatedHostingSubscription_bad_method(self):
    instance = self._makeInstance()
    fake_request = do_fake_request("POST")
    result = instance.Instance_getHateoasRelatedHostingSubscription(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 405)
    self.assertEquals(result, "")

  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoasRelatedHostingSubscription_not_instance_context(self):
    fake_request = do_fake_request("GET")
    result = self.portal.Instance_getHateoasRelatedHostingSubscription(REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 403)
    self.assertEquals(result, "")

  @simulate('Base_getRequestUrl', '*args, **kwargs',
      'return "http://example.org/bar"')
  @simulate('Base_getRequestHeader', '*args, **kwargs',
            'return "application/hal+json"')
  @changeSkin('Hal')
  def test_getHateoasRelatedHostingSubscription_result(self):
    subscription = self._makeHostingSubscription()
    instance= self._makeInstance()
    instance.edit(specialise_value=subscription)
    self.tic()
    fake_request = do_fake_request("GET")
    result = instance.Instance_getHateoasRelatedHostingSubscription(
        REQUEST=fake_request)
    self.assertEquals(fake_request.RESPONSE.status, 200)
    self.assertEquals(fake_request.RESPONSE.getHeader('Content-Type'),
      "application/hal+json"
    )

    self.assertEquals(json.loads(result), json.loads(json.dumps({
      '_links': {
        "self": {
          "href": "http://example.org/bar"
        },
        "index": {
          "href": "urn:jio:get:%s" % \
            instance.getRelativeUrl(),
          "title": "Software Instance"
        },
        "action_object_jump": {
          'href': "%s/ERP5Document_getHateoas" % subscription.getAbsoluteUrl(),
          'title': "Hosting Subscription"
        }
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
    self._addERP5Login(instance)
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
          "href": "urn:jio:get:%s" % instance.getRelativeUrl(),
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
          "href": "urn:jio:get:%s" % \
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
          "href": "urn:jio:get:%s" % computer.getRelativeUrl(),
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
          "href": "urn:jio:get:%s" % software_installation.getRelativeUrl(),
          "title": "Software Installation"
        },
      },
    }, indent=2)))

