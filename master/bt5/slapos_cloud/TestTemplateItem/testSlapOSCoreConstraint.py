# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Nexedi SA and Contributors. All Rights Reserved.
#
##############################################################################
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin

def getMessageList(o):
  return [str(q.getMessage()) for q in o.checkConsistency()]

class TestSlapOSSoftwareInstanceConstraint(testSlapOSMixin):
  def test_sla_xml(self):
    software_instance = self.portal.software_instance_module.newContent(
      portal_type='Software Instance')

    # fetch basic list of consistency messages
    current_message_list = getMessageList(software_instance)

    consistency_message = "Sla XML is invalid: Start tag expected, '<' not "\
        "found, line 1, column 1"

    # test the test: no expected message found
    self.assertFalse(consistency_message in current_message_list)

    software_instance.edit(sla_xml='this is bad xml')
    self.assertTrue(consistency_message in getMessageList(software_instance))

    software_instance.edit(sla_xml=self.generateEmptyXml())
    self.assertFalse(consistency_message in getMessageList(software_instance))
    self.assertSameSet(current_message_list, getMessageList(software_instance))

    software_instance.edit(sla_xml=None)
    self.assertFalse(consistency_message in getMessageList(software_instance))
    self.assertSameSet(current_message_list, getMessageList(software_instance))

    software_instance.edit(sla_xml='')
    self.assertFalse(consistency_message in getMessageList(software_instance))
    self.assertSameSet(current_message_list, getMessageList(software_instance))
