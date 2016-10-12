# -*- coding: utf-8 -*-
# Copyright (c) 2002-2013 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin
import json
import httplib
import urlparse
import base64
from unittest import skip

def hateoasGetLinkFromLinks(links, title):
  if type(links) == dict:
    if links.get('title') == title:
      return links
    return
  for action in links:
    if action.get('title') == title:
      return action

def getRelativeUrlFromUrn(urn):
  urn_schema = 'urn:jio:get:'
  try:
    _, url = urn.split(urn_schema)
  except ValueError:
    return
  return url

class TestSlapOSHypermediaPersonScenario(testSlapOSMixin):

  def _makeUser(self):
    new_id = self.generateNewId()
    person_user = self.portal.person_module.template_member.\
                                 Base_createCloneDocument(batch_mode=1)
    person_user.edit(
      title="live_test_%s" % new_id,
      reference="live_test_%s" % new_id,
      password="live_test_%s" % new_id,
      default_email_text="live_test_%s@example.org" % new_id,
    )

    person_user.validate()
    for assignment in person_user.contentValues(portal_type="Assignment"):
      assignment.open()
    self.tic()
    return person_user

  @skip("Hypermedia is not supported anymore.")
  def test(self):
    erp5_person = self._makeUser()
    self.tic()
    self.portal.changeSkin('Hal')
    self.portal.ERP5Site_reindexSkinList()
    self.tic()

    authorization = 'Basic %s' % base64.b64encode(
      "%s:%s" % (erp5_person.getReference(), erp5_person.getReference()))
    content_type = "application/hal+json"

    api_scheme, api_netloc, api_path, api_query, \
        api_fragment = urlparse.urlsplit(self.portal.absolute_url())

    def getNewHttpConnection(api_netloc):
      if api_scheme == 'https':
        raise Exception('Please connect directly to the Zope server')
      connection = httplib.HTTPConnection(api_netloc)
      return connection

    #####################################################
    # Access the master home page hal
    #####################################################

    connection = getNewHttpConnection(api_netloc)
    connection.request(
      method='GET',
      url='%s/web_site_module/hateoas/Base_getHateoasMaster' % \
          self.portal.absolute_url(),
      headers={
       'Authorization': authorization,
       'Accept': content_type,
      },
      body="",
    )
    response = connection.getresponse()
    self.assertEquals(response.status, 200)
    self.assertEquals(response.getheader('Content-Type'), content_type)
    home_page_hal = json.loads(response.read())

    #####################################################
    # Fetch the user hal
    #####################################################

    user_link_dict = home_page_hal['_links']['me']
    self.assertNotEqual(user_link_dict, None)

    traverse_url_template = home_page_hal['_links']['traverse']['href']
    me_relative_url = getRelativeUrlFromUrn(user_link_dict['href'])
    me_url = traverse_url_template.replace(
        '{&relative_url,view}',
        '&relative_url=%s&view=view' % me_relative_url
    )

    connection = getNewHttpConnection(api_netloc)
    connection.request(
      method=user_link_dict.get('method', 'GET'),
      url=me_url,
      headers={
       'Authorization': authorization,
       'Accept': content_type,
      },
      body="",
    )
    response = connection.getresponse()
    self.assertEquals(response.status, 200)
    self.assertEquals(response.getheader('Content-Type'), content_type)
    user_hal = json.loads(response.read())

    #####################################################
    # Run method to request an hosting subscription
    #####################################################

    request_link_dict = hateoasGetLinkFromLinks(
        user_hal['_links']['action_object_slap_post'],
        'requestHateoasHostingSubscription'
    )
    self.assertNotEqual(request_link_dict, None)
    connection = getNewHttpConnection(api_netloc)
    connection.request(
      method=request_link_dict.get('method', 'POST'),
      url=request_link_dict['href'],
      headers={
       'Authorization': authorization,
       'Content-Type': 'application/json',
      },
      body=json.dumps({
        'software_release': 'http://example.orgé',
        'title': 'a great titleé',
        'software_type': 'fooé',
        'parameter': {'param1é': 'value1é', 'param2é': 'value2é'},
        'sla': {'param3é': 'value3é', 'param4é': 'value4é'},
        'slave': False,
        'status': 'started',
      }),
    )
    response = connection.getresponse()
 
    self.assertEquals(response.status, 201)

    self.tic()

    #####################################################
    # Get user's hosting subscription list
    #####################################################
    user_link_dict = hateoasGetLinkFromLinks(
        user_hal['_links']['action_object_slap'],
        'getHateoasHostingSubscriptionList'
    )
    self.assertNotEqual(user_link_dict, None)
    connection = getNewHttpConnection(api_netloc)
    connection.request(
      method=user_link_dict.get('method', 'GET'),
      url=user_link_dict['href'],
      headers={
       'Authorization': authorization,
       'Accept': content_type,
      },
      body="",
    )
    response = connection.getresponse()
 
    self.assertEquals(response.status, 200)
    self.assertEquals(response.getheader('Content-Type'), content_type)
    subscription_collection_hal = json.loads(response.read())

    #####################################################
    # Get user's hosting subscription
    #####################################################
    subscription_link_dict = subscription_collection_hal['_links']\
        ['content'][0]
    self.assertNotEqual(subscription_link_dict, None)
    connection = getNewHttpConnection(api_netloc)
    connection.request(
      method=subscription_link_dict.get('method', 'GET'),
      url=subscription_link_dict['href'],
      headers={
       'Authorization': authorization,
       'Accept': content_type,
      },
      body="",
    )
    response = connection.getresponse()
 
    self.assertEquals(response.status, 200)
    self.assertEquals(response.getheader('Content-Type'), content_type)
    subscription_hal = json.loads(response.read())

    #####################################################
    # Get hosting subscription's instance list
    #####################################################
    user_link_dict = hateoasGetLinkFromLinks(
        subscription_hal['_links']['action_object_slap'],
        'getHateoasInstanceList'
    )
    self.assertNotEqual(user_link_dict, None)
    connection = getNewHttpConnection(api_netloc)
    connection.request(
      method=user_link_dict.get('method', 'GET'),
      url=user_link_dict['href'],
      headers={
       'Authorization': authorization,
       'Accept': content_type,
      },
      body="",
    )
    response = connection.getresponse()
 
    self.assertEquals(response.status, 200)
    self.assertEquals(response.getheader('Content-Type'), content_type)
    instance_collection_hal = json.loads(response.read())

    #####################################################
    # Get instance
    #####################################################
    subscription_link_dict = instance_collection_hal['_links']\
        ['content'][0]
    self.assertNotEqual(subscription_link_dict, None)
    connection = getNewHttpConnection(api_netloc)
    connection.request(
      method=subscription_link_dict.get('method', 'GET'),
      url=subscription_link_dict['href'],
      headers={
       'Authorization': authorization,
       'Accept': content_type,
      },
      body="",
    )
    response = connection.getresponse()
 
    self.assertEquals(response.status, 200)
    self.assertEquals(response.getheader('Content-Type'), content_type)
    instance_hal = json.loads(response.read())

    #####################################################
    # Fetch instance informations
    #####################################################

    request_link_dict = hateoasGetLinkFromLinks(
        instance_hal['_links']['action_object_slap'],
        'getHateoasInformation'
    )
    self.assertNotEqual(request_link_dict, None)
    connection = getNewHttpConnection(api_netloc)
    connection.request(
      method=request_link_dict.get('method', 'GET'),
      url=request_link_dict['href'],
      headers={
       'Authorization': authorization,
       'Accept': content_type,
      },
      body="",
    )
    response = connection.getresponse()
 
    self.assertEquals(response.status, 200)
    self.assertEquals(response.getheader('Content-Type'), content_type)

    self.tic()

    #####################################################
    # Get instance news
    #####################################################
    news_link_dict = hateoasGetLinkFromLinks(
        instance_hal['_links']['action_object_slap'],
        'getHateoasNews'
    )
    self.assertNotEqual(news_link_dict, None)
    connection = getNewHttpConnection(api_netloc)
    connection.request(
      method=news_link_dict.get('method', 'GET'),
      url=news_link_dict['href'],
      headers={
       'Authorization': authorization,
       'Accept': content_type,
      },
      body="",
    )
    response = connection.getresponse()
 
    self.assertEquals(response.status, 200)
    self.assertEquals(response.getheader('Content-Type'), content_type)
    news_hal = json.loads(response.read())

    # We are going to check computer and software
    # First create a computer and a software. We could alternatively later
    # create them through hypermedia links
    self.login(erp5_person.getReference())
    self.portal.portal_slap.requestComputer(
                       "computer %s" % erp5_person.getReference())
    self.tic()
    computer = self.portal.portal_catalog(portal_type="Computer",
                   sort_on=[('creation_date','descending')])[0].getObject()
    self.tic()
    self.portal.portal_slap.supplySupply("http://foo.com/software.cfg",
                                         computer.getReference(), "available")
    self.tic()
    self.logout()

    #####################################################
    # Get user's computer list
    #####################################################
    user_link_dict = hateoasGetLinkFromLinks(
        user_hal['_links']['action_object_slap'],
        'getHateoasComputerList'
    )
    self.assertNotEqual(user_link_dict, None)
    connection = getNewHttpConnection(api_netloc)
    connection.request(
      method=user_link_dict.get('method', 'GET'),
      url=user_link_dict['href'],
      headers={
       'Authorization': authorization,
       'Accept': content_type,
      },
      body="",
    )
    response = connection.getresponse()
 
    self.assertEquals(response.status, 200)
    self.assertEquals(response.getheader('Content-Type'), content_type)
    computer_collection_hal = json.loads(response.read())

    #####################################################
    # Get user's computer
    #####################################################
    computer_link_dict = computer_collection_hal['_links']\
        ['content'][0]
    self.assertNotEqual(computer_link_dict, None)
    connection = getNewHttpConnection(api_netloc)
    connection.request(
      method=computer_link_dict.get('method', 'GET'),
      url=computer_link_dict['href'],
      headers={
       'Authorization': authorization,
       'Accept': content_type,
      },
      body="",
    )
    response = connection.getresponse()
 
    self.assertEquals(response.status, 200)
    self.assertEquals(response.getheader('Content-Type'), content_type)
    computer_hal = json.loads(response.read())

    #####################################################
    # Get computer's software list
    #####################################################
    computer_link_dict = hateoasGetLinkFromLinks(
        computer_hal['_links']['action_object_slap'],
        'getHateoasSoftwareInstallationList'
    )
    self.assertNotEqual(computer_link_dict, None)
    connection = getNewHttpConnection(api_netloc)
    connection.request(
      method=computer_link_dict.get('method', 'GET'),
      url=computer_link_dict['href'],
      headers={
       'Authorization': authorization,
       'Accept': content_type,
      },
      body="",
    )
    response = connection.getresponse()
 
    self.assertEquals(response.status, 200)
    self.assertEquals(response.getheader('Content-Type'), content_type)
    software_collection_hal = json.loads(response.read())

    #####################################################
    # Get user's software
    #####################################################
    software_link_dict = software_collection_hal['_links']\
        ['content'][0]
    self.assertNotEqual(software_link_dict, None)
    connection = getNewHttpConnection(api_netloc)
    connection.request(
      method=software_link_dict.get('method', 'GET'),
      url=software_link_dict['href'],
      headers={
       'Authorization': authorization,
       'Accept': content_type,
      },
      body="",
    )
    response = connection.getresponse()
    self.assertEquals(response.getheader('Content-Type'), content_type)
    software_hal = json.loads(response.read())


class TestSlapOSHypermediaInstanceScenario(testSlapOSMixin):
  def generateNewId(self):
    return "%s" % self.portal.portal_ids.generateNewId(
        id_group=('slapos_core_test'))

  def generateNewSoftwareReleaseUrl(self):
    return 'http://example.org/test%s.cfg' % self.generateNewId()

  def generateNewSoftwareType(self):
    return 'Type %s' % self.generateNewId()

  def generateNewSoftwareTitle(self):
    return 'Title %s' % self.generateNewId()

  def test(self):
    self._makeTree()
    instance = self.software_instance
    self.portal.changeSkin('Hal')
    self.portal.ERP5Site_reindexSkinList()
    self.tic()

    remote_user = instance.getReference()
    content_type = "application/hal+json"

    api_scheme, api_netloc, api_path, api_query, \
        api_fragment = urlparse.urlsplit(self.portal.absolute_url())

    def getNewHttpConnection(api_netloc):
      if api_scheme == 'https':
        raise Exception('Please connect directly to the Zope server')
      connection = httplib.HTTPConnection(api_netloc)
      return connection

    #####################################################
    # Access the master home page hal
    #####################################################

    connection = getNewHttpConnection(api_netloc)
    connection.request(
      method='GET',
      url='%s/web_site_module/hateoas/Base_getHateoasMaster' % \
          self.portal.absolute_url(),
      headers={
       'REMOTE_USER': remote_user,
       'Accept': content_type,
      },
      body="",
    )
    response = connection.getresponse()
    self.assertEquals(response.status, 200)
    self.assertEquals(response.getheader('Content-Type'), content_type)
    home_page_hal = json.loads(response.read())

    #####################################################
    # Fetch the instance hal
    #####################################################

    user_link_dict = home_page_hal['_links']['me']
    self.assertNotEqual(user_link_dict, None)

    traverse_url_template = home_page_hal['_links']['traverse']['href']
    me_relative_url = getRelativeUrlFromUrn(user_link_dict['href'])
    me_url = traverse_url_template.replace(
        '{&relative_url,view}',
        '&relative_url=%s&view=view' % me_relative_url
    )

    connection = getNewHttpConnection(api_netloc)
    connection.request(
      method=user_link_dict.get('method', 'GET'),
      url=me_url,
      headers={
       'REMOTE_USER': remote_user,
       'Accept': content_type,
      },
      body="",
    )
    response = connection.getresponse()
    self.assertEquals(response.status, 200)
    self.assertEquals(response.getheader('Content-Type'), content_type)
    instance_hal = json.loads(response.read())

    #####################################################
    # Fetch instance informations
    #####################################################

    user_link_dict = hateoasGetLinkFromLinks(
        instance_hal['_links']['action_object_slap'],
        'getHateoasInformation'
    )
    self.assertNotEqual(user_link_dict, None)
    connection = getNewHttpConnection(api_netloc)
    connection.request(
      method=user_link_dict.get('method', 'GET'),
      url=user_link_dict['href'],
      headers={
       'REMOTE_USER': remote_user,
       'Accept': content_type,
      },
      body="",
    )
    response = connection.getresponse()
 
    self.assertEquals(response.status, 200)
    self.assertEquals(response.getheader('Content-Type'), content_type)

    self.tic()

    #####################################################
    # Get instance news
    #####################################################
    user_link_dict = hateoasGetLinkFromLinks(
        instance_hal['_links']['action_object_slap'],
        'getHateoasNews'
    )
    self.assertNotEqual(user_link_dict, None)
    connection = getNewHttpConnection(api_netloc)
    connection.request(
      method=user_link_dict.get('method', 'GET'),
      url=user_link_dict['href'],
      headers={
       'REMOTE_USER': remote_user,
       'Accept': content_type,
      },
      body="",
    )
    response = connection.getresponse()
 
    self.assertEquals(response.status, 200)
    self.assertEquals(response.getheader('Content-Type'), content_type)

    self.tic()

    #####################################################
    # Get hosting subscription of instance
    #####################################################
    # XXX can be simpler and doesn't need getHateoasRelatedHostingSubscription script
    hosting_link_dict = hateoasGetLinkFromLinks(
        instance_hal['_links']['action_object_slap'],
        'getHateoasRelatedHostingSubscription'
    )
    self.assertNotEqual(hosting_link_dict, None)
    connection = getNewHttpConnection(api_netloc)
    connection.request(
      method=hosting_link_dict.get('method', 'GET'),
      url=hosting_link_dict['href'],
      headers={
       'REMOTE_USER': remote_user,
       'Accept': content_type,
      },
      body="",
    )
    response = connection.getresponse()
 
    self.assertEquals(response.status, 200)
    self.assertEquals(response.getheader('Content-Type'), content_type)
    subscription_hal = json.loads(response.read())

    self.tic()


    hosting_link_dict = hateoasGetLinkFromLinks(
        subscription_hal['_links']['action_object_jump'],
        'Hosting Subscription'
    )
    self.assertNotEqual(hosting_link_dict, None)
    connection = getNewHttpConnection(api_netloc)
    connection.request(
      method=hosting_link_dict.get('method', 'GET'),
      url=hosting_link_dict['href'],
      headers={
       'REMOTE_USER': remote_user,
       'Accept': content_type,
      },
      body="",
    )
    response = connection.getresponse()
 
    self.assertEquals(response.status, 200)
    self.assertEquals(response.getheader('Content-Type'), content_type)
    subscription_hal = json.loads(response.read())

    self.tic()

    #####################################################
    # Get hosting subscription's instance list
    #####################################################
    user_link_dict = hateoasGetLinkFromLinks(
        subscription_hal['_links']['action_object_slap'],
        'getHateoasInstanceList'
    )
    self.assertNotEqual(user_link_dict, None)
    connection = getNewHttpConnection(api_netloc)
    connection.request(
      method=user_link_dict.get('method', 'GET'),
      url=user_link_dict['href'],
      headers={
       'REMOTE_USER': remote_user,
       'Accept': content_type,
      },
      body="",
    )
    response = connection.getresponse()
 
    self.assertEquals(response.status, 200)
    self.assertEquals(response.getheader('Content-Type'), content_type)
    instance_collection_hal = json.loads(response.read())

    #####################################################
    # Get instance
    #####################################################
    subscription_link_dict = instance_collection_hal['_links']\
        ['content'][0]
    self.assertNotEqual(subscription_link_dict, None)
    connection = getNewHttpConnection(api_netloc)
    connection.request(
      method=subscription_link_dict.get('method', 'GET'),
      url=subscription_link_dict['href'],
      headers={
       'REMOTE_USER': remote_user,
       'Accept': content_type,
      },
      body="",
    )
    response = connection.getresponse()
 
    self.assertEquals(response.status, 200)
    self.assertEquals(response.getheader('Content-Type'), content_type)
    instance_hal = json.loads(response.read())

