# Copyright (c) 2002-2012 Nexedi SA and Contributors. All Rights Reserved.
import transaction
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin

class TestSlapOSCorePromiseSlapOSModuleIdGeneratorAlarm(testSlapOSMixin):
  def test_Module_assertIdGenerator(self):
    self.login()
    module = self.portal.newContent(portal_type='Person Module',
        id=str(self.generateNewId()),
        id_generator='bad_id_generator')

    self.assertEqual('bad_id_generator', module.getIdGenerator())

    # check positive response
    self.assertTrue(module.Module_assertIdGenerator('bad_id_generator', False))
    self.assertEqual('bad_id_generator', module.getIdGenerator())
    self.assertTrue(module.Module_assertIdGenerator('bad_id_generator', True))
    self.assertEqual('bad_id_generator', module.getIdGenerator())

    # check negative response and that no-op run does not modify
    self.assertFalse(module.Module_assertIdGenerator('good_id_generator', False))
    self.assertEqual('bad_id_generator', module.getIdGenerator())

    # check negative response with fixit request
    self.assertFalse(module.Module_assertIdGenerator('good_id_generator', True))
    self.assertEqual('good_id_generator', module.getIdGenerator())
    self.assertTrue(module.Module_assertIdGenerator('good_id_generator', False))
    self.assertEqual('good_id_generator', module.getIdGenerator())

    transaction.abort()
