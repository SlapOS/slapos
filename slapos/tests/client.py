##############################################################################
#
# Copyright (c) 2010 Vifib SARL and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
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

import logging
import unittest
import slapos.slap
import slapos.client

class TestClient(unittest.TestCase):
  def setUp(self):
    self.called_software_product = None

    class FakeSoftwareProductCollection(object):
      def __init__(inner_self, *args, **kw_args):
        inner_self.__getattr__ = inner_self.get
      def get(inner_self, software_product):
        self.called_software_product = software_product
        return self.software_product_reference


    self.slap = slapos.slap.slap()
    self.product_collection = FakeSoftwareProductCollection(
        logging.getLogger(), self.slap)


  def test_getSoftwareReleaseFromSoftwareString_softwareProduct(self):
    """
    Test that if given software is a Sofwtare Product (i.e matching
    the magic string), it returns the corresponding value of a call to
    SoftwareProductCollection.
    """
    self.software_product_reference = 'foo'
    software_string = '%s%s' % (
        slapos.client.SOFTWARE_PRODUCT_NAMESPACE,
        self.software_product_reference
    )

    slapos.client._getSoftwareReleaseFromSoftwareString(
        logging.getLogger(), software_string, self.product_collection)

    self.assertEqual(
        self.called_software_product,
        self.software_product_reference
    )

  def test_getSoftwareReleaseFromSoftwareString_softwareProduct_emptySoftwareProduct(self):
    """
    Test that if given software is a Software Product (i.e matching
    the magic string), but this software product is empty, it exits.
    """
    self.software_product_reference = 'foo'
    software_string = '%s%s' % (
        slapos.client.SOFTWARE_PRODUCT_NAMESPACE,
        self.software_product_reference
    )

    def fake_get(software_product):
      raise AttributeError()
    self.product_collection.__getattr__ = fake_get

    self.assertRaises(
        SystemExit,
        slapos.client._getSoftwareReleaseFromSoftwareString,
        logging.getLogger(), software_string, self.product_collection
    )

  def test_getSoftwareReleaseFromSoftwareString_softwareRelease(self):
    """
    Test that if given software is a simple Software Release URL (not matching
    the magic string), it is just returned without modification.
    """
    software_string = 'foo'
    returned_value = slapos.client._getSoftwareReleaseFromSoftwareString(
        logging.getLogger(), software_string, self.product_collection)

    self.assertEqual(
        self.called_software_product,
        None
    )

    self.assertEqual(
        returned_value,
        software_string
    )
