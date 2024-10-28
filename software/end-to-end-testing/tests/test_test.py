import unittest


class Test(unittest.TestCase):

  def test_fail(self):
    self.assertEqual(0, 1)

  def test_succeed(self):
    self.assertEqual(0, 0)
