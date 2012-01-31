from Products.ERP5Type.tests.Sequence import SequenceList
import unittest
from testVifibSlapWebService import TestVifibSlapWebServiceMixin
from Products.DCWorkflow.DCWorkflow import ValidationFailed
from random import random
from slapos import slap

class TestVifibSlapComputerPartitionLock(TestVifibSlapWebServiceMixin):

  def test_lock_building(self):
    """Check locking building computer partition

    It shall render it as stopped and disallow any operation.

    Destruction shall be possible.
    """
    raise NotImplementedError

  def test_lock_stopping(self):
    """Check locking stopping computer partition

    It shall render it as stopped and disallow any operation.

    Stopping shall be possible.

    Destruction shall be possible.
    """
    raise NotImplementedError

  def test_lock_stopped(self):
    """Check locking stopped computer partition

    It shall render it as stopped and disallow any operation.

    Destruction shall be possible.
    """
    raise NotImplementedError

  def test_lock_starting(self):
    """Check locking starting computer partition

    It shall render it as stopped and disallow any operation.

    Stopping shall be possible.

    Destruction shall be possible.
    """
    raise NotImplementedError

  def test_lock_started(self):
    """Check locking started computer partition

    It shall render it as stopped and disallow starting.

    Stopping shall be possible.

    Destruction shall be possible.
    """
    raise NotImplementedError

  def test_lock_destroying(self):
    """Check locking destroying computer partition

    It shall render it as destroyed.

    Destruction shall be possible.
    """
    raise NotImplementedError

  def test_lock_destroyed(self):
    """Check locking destroyed computer partition

    It shall not render it at all.
    """
    raise NotImplementedError

  def test_lock_update(self):
    """Check locking update computer partition

    It shall render as stopped.

    Destruction shall be possible.
    """
    raise NotImplementedError

def test_suite():
  suite = unittest.TestSuite()
  suite.addTest(unittest.makeSuite(TestVifibSlapComputerPartitionLock))
  return suite
