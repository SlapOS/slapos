from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin
from slapos import slap
from slapos.slap.slap import Supply
from Products.ZSQLCatalog.SQLCatalog import Query, ComplexQuery

class TestVifibSlapSupply(TestVifibSlapWebServiceMixin):
  ########################################
  # slap.registerSupply
  ########################################

  def test_slap_registerSupply(self):
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    supply = self.slap.registerSupply()
    self.assertTrue(isinstance(supply, Supply))

  ########################################
  # Supply.supply
  ########################################

  def stepSupplyComputerSoftwareReleaseAvailable(self, sequence, **kw):
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    supply = self.slap.registerSupply()
    supply.supply(sequence['software_release_uri'],
      sequence['computer_reference'], 'available')

  def stepSupplyComputerSoftwareReleaseDestroyed(self, sequence, **kw):
    self.slap = slap.slap()
    self.slap.initializeConnection(self.server_url, timeout=None)
    supply = self.slap.registerSupply()
    supply.supply(sequence['software_release_uri'],
      sequence['computer_reference'], 'destroyed')

  def test_Supply_supply(self):
    sequence_list = SequenceList()
    sequence_string = self.prepare_formated_computer + \
      self.prepare_published_software_release + """
      SlapLoginCurrentComputer
      CheckEmptyComputerGetSoftwareReleaseListCall
      SlapLogout

      SlapLoginTestVifibAdmin
      SupplyComputerSoftwareReleaseAvailable
      Tic
      SlapLogout

      SlapLoginCurrentComputer
      CheckSuccessComputerGetSoftwareReleaseListCall
      SlapLogout

      SlapLoginTestVifibAdmin
      SupplyComputerSoftwareReleaseDestroyed
      Tic
      SlapLogout

      SlapLoginCurrentComputer
      CheckDestroyedStateGetSoftwareReleaseListCall
      SlapLogout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

  def _checkOnePurchasePackingList(self, sequence, resource_uid):
    self.assertEqual(1,
      self.portal.portal_catalog.countResults(
        portal_type='Purchase Packing List Line',
        simulation_state='confirmed',
        default_resource_uid=resource_uid,
        default_aggregate_uid=ComplexQuery(
          Query(default_aggregate_uid=sequence['computer_uid']),
          Query(default_aggregate_uid=sequence['software_release_uid']),
          operator='AND')
        )[0][0]
    )
  def stepCheckOneConfirmedSetupPurchasePackingListLineComputerSoftwareRelease(
      self, sequence, **kw):
    self._checkOnePurchasePackingList(sequence, self.portal.restrictedTraverse(
      self.portal.portal_preferences.getPreferredSoftwareSetupResource()
    ).getUid())

  def stepCheckOneConfirmedCleanupPurchasePackingListLineComputerSoftwareRelease(
      self, sequence, **kw):
    self._checkOnePurchasePackingList(sequence, self.portal.restrictedTraverse(
      self.portal.portal_preferences.getPreferredSoftwareCleanupResource()
    ).getUid())

  def test_Supply_supply_twice(self):
    sequence_list = SequenceList()
    sequence_string = self.prepare_formated_computer + \
      self.prepare_published_software_release + """
      SlapLoginCurrentComputer
      CheckEmptyComputerGetSoftwareReleaseListCall
      SlapLogout

      SlapLoginTestVifibAdmin
      SupplyComputerSoftwareReleaseAvailable
      Tic
      SupplyComputerSoftwareReleaseAvailable
      Tic
      SlapLogout

      SlapLoginCurrentComputer
      CheckSuccessComputerGetSoftwareReleaseListCall
      SlapLogout

      LoginDefaultUser
      CheckOneConfirmedSetupPurchasePackingListLineComputerSoftwareRelease
      Logout

      SlapLoginTestVifibAdmin
      SupplyComputerSoftwareReleaseDestroyed
      Tic
      SupplyComputerSoftwareReleaseDestroyed
      Tic
      SlapLogout

      SlapLoginCurrentComputer
      CheckDestroyedStateGetSoftwareReleaseListCall
      SlapLogout

      LoginDefaultUser
      CheckOneConfirmedCleanupPurchasePackingListLineComputerSoftwareRelease
      Logout

      LoginERP5TypeTestCase
      CheckSiteConsistency
      Logout
      """
    sequence_list.addSequenceString(sequence_string)
    sequence_list.play(self)

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapSupply))
  return suite
