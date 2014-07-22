# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
from Products.SlapOS.tests.testSlapOSMixin import testSlapOSMixin
from AccessControl import getSecurityManager
from DateTime import DateTime
import transaction

class TestSoftwareReleaseListFromSoftwareProduct(testSlapOSMixin):
  def afterSetUp(self):
    super(TestSoftwareReleaseListFromSoftwareProduct, self).afterSetUp()
    self.user_id = getSecurityManager().getUser().getId()

  def beforeTearDown(self):
    transaction.abort()

  def generateNewId(self):
    return self.getPortalObject().portal_ids.generateNewId(
                                     id_group=('slapos_core_test'))
  
  def test_getSortedSoftwareReleaseListFromSoftwareProduct(self):
    new_id = self.generateNewId()
    software_product = self._makeSoftwareProduct(new_id)
    release_list = software_product.SoftwareProduct_getSortedSoftwareReleaseList(
      software_product.getReference())
    self.assertEqual(release_list, [])
    
    # published software release
    software_release1 = self._makeSoftwareRelease(new_id)
    software_release1.edit(
        aggregate_value=software_product.getRelativeUrl(),
        url_string='http://example.org/1.cfg'
    )
    software_release1.publish()
    software_release2 = self._makeSoftwareRelease(self.generateNewId())
    software_release2.edit(
        aggregate_value=software_product.getRelativeUrl(),
        url_string='http://example.org/2.cfg'
    )
    software_release2.publish()
    # 1 released software release, should not appear
    software_release3 = self._makeSoftwareRelease(new_id)
    self.assertTrue(software_release3.getValidationState() == 'released')
    software_release3.edit(
        aggregate_value=software_product.getRelativeUrl(),
        url_string='http://example.org/3.cfg'
    )
    self.tic()

    release_list = software_product.SoftwareProduct_getSortedSoftwareReleaseList(
      software_product.getReference())
    self.assertEquals([release.getUrlString() for release in release_list],
          ['http://example.org/2.cfg', 'http://example.org/1.cfg'])
    
    
  def test_getSortedSoftwareReleaseListFromSoftwareProduct_Changed(self):
    new_id = self.generateNewId()
    software_product = self._makeSoftwareProduct(new_id)
    release_list = software_product.SoftwareProduct_getSortedSoftwareReleaseList(
      software_product.getReference())
    self.assertEqual(release_list, [])
    
    # 2 published software releases
    software_release2 = self._makeSoftwareRelease(self.generateNewId())
    software_release2.publish()
    software_release2.edit(
        aggregate_value=software_product.getRelativeUrl(),
        url_string='http://example.org/2.cfg'
    )
    # Newest software release
    software_release1 = self._makeSoftwareRelease(new_id)
    software_release1.publish()
    software_release1.edit(
        aggregate_value=software_product.getRelativeUrl(),
        url_string='http://example.org/1.cfg'
    )
    self.tic()

    release_list = software_product.SoftwareProduct_getSortedSoftwareReleaseList(
      software_product.getReference())
    self.assertEquals([release.getUrlString() for release in release_list],
          ['http://example.org/1.cfg', 'http://example.org/2.cfg'])
