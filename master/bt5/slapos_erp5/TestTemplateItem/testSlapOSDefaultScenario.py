# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
#
##############################################################################

from testSlapOSSecurityGroup import TestSlapOSSecurityMixin
import re
from xml_marshaller import xml_marshaller

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

class TestSlapOSDefaultScenario(TestSlapOSSecurityMixin):
  def joinSlapOS(self, web_site, reference):
    def findMessage(email, body):
      for candidate in reversed(self.portal.MailHost.getMessageList()):
        if email in candidate[1] \
            and body in candidate[2]:
          return candidate[2]

    credential_request_form = self.web_site.ERP5Site_viewCredentialRequestForm()

    self.assertTrue('Vifib Cloud is a distributed cloud around the'
        in credential_request_form)

    email = '%s@example.com' % reference

    request = web_site.ERP5Site_newCredentialRequest(
      reference=reference,
      default_email_text=email
    )

    self.assertTrue('Thanks%20for%20your%20registration.%20You%20will%20be%2'
        '0receive%20an%20email%20to%20activate%20your%20account.' in request)

    self.tic()

    to_click_message = findMessage(email, 'You have requested one user')

    self.assertNotEqual(None, to_click_message)

    to_click_url = re.search('href="(.+?)"', to_click_message).group(1)

    self.assertTrue('ERP5Site_activeLogin' in to_click_url)

    join_key = to_click_url.split('=')[-1]

    web_site.ERP5Site_activeLogin(key=join_key)

    self.tic()

    welcome_message = findMessage(email, "de votre nouveau compte ERP5")
    self.assertNotEqual(None, welcome_message)

  def requestComputer(self, title):
    requestXml = self.portal.portal_slap.requestComputer(title)
    self.tic()
    self.assertTrue('marshal' in requestXml)
    computer = xml_marshaller.loads(requestXml)
    computer_id = getattr(computer, '_computer_id', None)
    self.assertNotEqual(None, computer_id)
    return computer_id

  def supplySoftware(self, server, url, state='available'):
    self.portal.portal_slap.supplySupply(url, server.getReference(), state)
    self.tic()

    software_installation = self.portal.portal_catalog.getResultValue(
        portal_type='Software Installation',
        url_string=url,
        default_aggregate_uid=server.getUid())

    self.assertNotEqual(None, software_installation)

    if state=='available':
      self.assertEqual('start_requested', software_installation.getSlapState())
    else:
      self.assertEqual('destroy_requested', software_installation.getSlapState())

  @changeSkin('Hosting')
  def setServerOpenPublic(self, server):
    server.Computer_updateAllocationScope(
        allocation_scope='open/public', subject_list=[])
    self.assertEqual('open/public', server.getAllocationScope())
    self.assertEqual('close', server.getCapacityScope())

  @changeSkin('Hosting')
  def setServerOpenPersonal(self, server):
    server.Computer_updateAllocationScope(
        allocation_scope='open/personal', subject_list=[])
    self.assertEqual('open/personal', server.getAllocationScope())
    self.assertEqual('open', server.getCapacityScope())

  @changeSkin('Hosting')
  def setServerOpenFriend(self, server, friend_list=None):
    if friend_list is None:
      friend_list = []
    server.Computer_updateAllocationScope(
        allocation_scope='open/friend', subject_list=friend_list)
    self.assertEqual('open/friend', server.getAllocationScope())
    self.assertEqual('open', server.getCapacityScope())
    self.assertSameSet(friend_list, server.getSubjectList())

  def test(self):
    # some preparation
    self.logout()
    self.web_site = self.portal.web_site_module.hosting

    # lets join as owner, which will own few computers
    owner_reference = 'owner-%s' % self.generateNewId()
    self.joinSlapOS(self.web_site, owner_reference)

    # hooray, now it is time to create computers
    self.login(owner_reference)

    public_server_title = 'Public Server for %s' % owner_reference
    public_server_id = self.requestComputer(public_server_title)
    public_server = self.portal.portal_catalog.getResultValue(
        portal_type='Computer', reference=public_server_id)
    self.assertNotEqual(None, public_server)
    self.setServerOpenPublic(public_server)

    personal_server_title = 'Personal Server for %s' % owner_reference
    personal_server_id = self.requestComputer(personal_server_title)
    personal_server = self.portal.portal_catalog.getResultValue(
        portal_type='Computer', reference=personal_server_id)
    self.assertNotEqual(None, personal_server)
    self.setServerOpenPersonal(personal_server)

    friend_server_title = 'Friend Server for %s' % owner_reference
    friend_server_id = self.requestComputer(friend_server_title)
    friend_server = self.portal.portal_catalog.getResultValue(
        portal_type='Computer', reference=friend_server_id)
    self.assertNotEqual(None, friend_server)
    self.setServerOpenFriend(friend_server)

    # and install some software on them

    public_server_software = self.generateNewSoftwareReleaseUrl()
    self.supplySoftware(public_server, public_server_software)

    personal_server_software = self.generateNewSoftwareReleaseUrl()
    self.supplySoftware(personal_server, personal_server_software)

    friend_server_software = self.generateNewSoftwareReleaseUrl()
    self.supplySoftware(friend_server, friend_server_software)
    # remove the assertion after test is finished
    self.assertTrue(False, 'Test not finished')
