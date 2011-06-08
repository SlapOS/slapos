# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010 Nexedi SA and Contributors. All Rights Reserved.
#                    Romain Courteaud <romain@nexedi.com>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
import unittest
from VifibMixin import testVifibMixin

HTTP_OK = 200
MOVED_TEMPORARILY = 302


class TestVifibWebSite(testVifibMixin):
  web_site_portal_type = "Web Site"
  auth = 'ERP5TypeTestCase:'

  def getTitle(self):
    return "Vifib WebSite"

  def test_01_checkERP5Access(self):
    """
    Test default ERP5 page
    """
    response = self.publish('/%s' % \
                    self.portal.getId(), self.auth)

    self.assertEquals(HTTP_OK, response.getStatus())
    self.assertTrue(response.getHeader('content-type').startswith('text/html'))
    self.assertTrue("Welcome to ERP5" in response.getBody())

  def test_02_checkCashCloudAccess(self):
    """
    Test Cash access
    """
    module = self.portal.getDefaultModule(self.web_site_portal_type)
    web_site = getattr(module, 'cash')
    #Check web site is present
    self.assertTrue(web_site is not None, "Website not found")

    # Test anonymous
    response = self.publish('/%s/%s' % \
                    (self.portal.getId(), web_site.getRelativeUrl())
                     )

    self.assertEquals(HTTP_OK, response.getStatus())
    self.assertEquals('text/html; charset=utf-8',
                      response.getHeader('content-type'))
    self.assertTrue("Website is under construction..." in response.getBody())

  def test_04_checkHostingAccess(self):
    """
    Test Hosting Access
    """
    module = self.portal.getDefaultModule(self.web_site_portal_type)
    web_site = getattr(module, 'hosting')
    #Check web site is present
    self.assertTrue(web_site is not None, "Website not found")

    # Test anonymous
    response = self.publish('/%s/%s' % \
                    (self.portal.getId(), web_site.getRelativeUrl())
                     )

    self.assertEquals(HTTP_OK, response.getStatus())
    self.assertEquals('text/html; charset=utf-8',
                      response.getHeader('content-type'))
    self.assertTrue("My Services" in response.getBody())

  def test_05_checkFreeFiberAccess(self):
    """
    Test Free Fiber access
    """
    module = self.portal.getDefaultModule(self.web_site_portal_type)
    web_site = getattr(module, 'fiber')
    #Check web site is present
    self.assertTrue(web_site is not None, "Website not found")

    # Test anonymous
    response = self.publish('/%s/%s' % \
                    (self.portal.getId(), web_site.getRelativeUrl())
                     )

    self.assertEquals(HTTP_OK, response.getStatus())
    self.assertEquals('text/html; charset=utf-8',
                      response.getHeader('content-type'))
    self.assertTrue("Je veux la fibre gratuite avec ViFiB" in
        response.getBody())

  def test_06_checkERPypiAccess(self):
    """
    Test ERPypi access
    """
    module = self.portal.getDefaultModule(self.web_site_portal_type)
    web_site = getattr(module, 'erpypi')
    #Check web site is present
    self.assertTrue(web_site is not None, "Website not found")

    # Test anonymous
    response = self.publish('/%s/%s' % \
                    (self.portal.getId(), web_site.getRelativeUrl())
                     )

    self.assertEquals(HTTP_OK, response.getStatus())
    self.assertEquals('text/html; charset=utf-8',
                      response.getHeader('content-type'))
    self.assertTrue("Home" in response.getBody())


def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibWebSite))
  return suite
