# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
#
##############################################################################

from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin

class TestOpenSaleOrderManagement(testSlapOSMixin):
  def test_noOSO_newPerson(self):
    person = self.portal.person_module.newContent(portal_type='Person',
        reference='TESTP-%s' % self.generateNewId())
    person.validate()
    self.tic()

    self.assertEqual(None, self.portal.portal_catalog.getResultValue(
        portal_type='Open Sale Order',
        default_destination_section_uid=person.getUid()
    ))

  def test_noOSO_after_fixConsistency(self):
    person = self.portal.person_module.newContent(portal_type='Person',
        reference='TESTP-%s' % self.generateNewId())
    person.validate()
    self.tic()
    person.fixConsistency()
    self.tic()

    self.assertEqual(None, self.portal.portal_catalog.getResultValue(
        portal_type='Open Sale Order',
        default_destination_section_uid=person.getUid()
    ))

  def test_OSO_after_Person_updateOpenSaleOrder(self):
    person = self.portal.person_module.newContent(portal_type='Person',
        reference='TESTP-%s' % self.generateNewId())
    person.validate()
    self.tic()

    person.Person_updateOpenSaleOrder()
    self.tic()

    open_sale_order_list = self.portal.portal_catalog(
        validation_state='validated',
        portal_type='Open Sale Order',
        default_destination_section_uid=person.getUid()
    )
    self.assertEqual(1, len(open_sale_order_list))
    open_sale_order = open_sale_order_list[0]

    self.assertEqual('SlapOS Subscription Open Sale Order',
        open_sale_order.getTitle())
