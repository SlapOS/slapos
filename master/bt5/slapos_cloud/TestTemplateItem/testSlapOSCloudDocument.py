# -*- coding: utf-8 -*-
# Copyright (c) 2013 Nexedi SA and Contributors. All Rights Reserved.
import transaction
from Products.SlapOS.tests.testSlapOSMixin import \
  testSlapOSMixin

class TestSlapOSPersonDocument(testSlapOSMixin):

  def beforeTearDown(self):
    transaction.abort()

  def test_getTitle(self):
    person = self.portal.person_module.newContent(
        portal_type="Person")

    # Default title is empty
    self.assertEquals(person.getTitle(), None)

    # If not title, the email is used
    person.edit(default_email_coordinate_text="foo@example.org")
    self.assertEquals(person.getTitle(), 'foo@example.org')

    # But if first name, last name are set, use them
    person.edit(first_name="foo", last_name="bar")
    self.assertEquals(person.getTitle(), 'foo bar')

    # Finally, if the title is set
    person.edit(title="foobar")
    self.assertEquals(person.getTitle(), 'foobar')
