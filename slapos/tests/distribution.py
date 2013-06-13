# -*- coding: utf-8 -*-

import unittest
from slapos.grid import distribution


class TestDebianize(unittest.TestCase):
    def test_debian_major(self):
        """
        On debian, we only care about major release.
        All the other tuples are unchanged.
        """
        for provided, expected in [
            (('CentOS', '6.3', 'Final'), None),
            (('Ubuntu', '12.04', 'precise'), None),
            (('Ubuntu', '13.04', 'raring'), None),
            (('Fedora', '17', 'Beefy Miracle'), None),
            (('debian', '6.0.6', ''), ('debian', '6', '')),
            (('debian', '7.0', ''), ('debian', '7', '')),
        ]:
            self.assertEqual(distribution._debianize(provided), expected or provided)


class TestOSMatches(unittest.TestCase):
    def test_centos(self):
        self.assertFalse(distribution.os_matches(('CentOS', '6.3', 'Final'),
                                                 ('Ubuntu', '13.04', 'raring')))
        self.assertFalse(distribution.os_matches(('CentOS', '6.3', 'Final'),
                                                 ('debian', '6.3', '')))

    def test_ubuntu(self):
        self.assertFalse(distribution.os_matches(('Ubuntu', '12.04', 'precise'),
                                                 ('Ubuntu', '13.04', 'raring')))
        self.assertTrue(distribution.os_matches(('Ubuntu', '13.04', 'raring'),
                                                ('Ubuntu', '13.04', 'raring')))
        self.assertTrue(distribution.os_matches(('Ubuntu', '12.04', 'precise'),
                                                ('Ubuntu', '12.04', 'precise')))

    def test_debian(self):
        self.assertFalse(distribution.os_matches(('debian', '6.0.6', ''),
                                                 ('debian', '7.0', '')))
        self.assertTrue(distribution.os_matches(('debian', '6.0.6', ''),
                                                ('debian', '6.0.5', '')))
        self.assertTrue(distribution.os_matches(('debian', '6.0.6', ''),
                                                ('debian', '6.1', '')))
