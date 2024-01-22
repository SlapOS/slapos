import json
import os
import shutil
import tempfile
import unittest

import zc.buildout.testing
import zc.buildout.buildout
import passlib.hash
from slapos.recipe import random


class TestPassword(unittest.TestCase):
  def setUp(self):
    self.buildout = zc.buildout.testing.Buildout()
    parts_directory = tempfile.mkdtemp()
    self.buildout['buildout']['parts-directory'] = parts_directory
    self.addCleanup(shutil.rmtree, parts_directory)

  def _makeRecipe(self, options, section_name="random"):
    self.buildout[section_name] = options
    recipe = random.Password(
      self.buildout, section_name, self.buildout[section_name]
    )
    return recipe

  def test_empty_options(self):
    recipe = self._makeRecipe({})
    passwd = self.buildout["random"]["passwd"]
    self.assertEqual(len(passwd), 16)
    recipe.install()
    with open(self.buildout["random"]["storage-path"]) as f:
      self.assertEqual(json.load(f), {'': passwd})

  def test_storage_path(self):
    tf = tempfile.NamedTemporaryFile(delete=False)
    self.addCleanup(os.unlink, tf.name)
    self._makeRecipe({'storage-path': tf.name}).install()
    passwd = self.buildout["random"]["passwd"]
    self.assertEqual(len(passwd), 16)
    with open(tf.name) as f:
      self.assertEqual(json.load(f), {'': passwd})

    self._makeRecipe({'storage-path': tf.name}, "another").install()
    self.assertEqual(self.buildout["another"]["passwd"], passwd)

  def test_storage_path_legacy_format(self):
    with tempfile.NamedTemporaryFile(delete=False) as tf:
      tf.write(b'secret\n')
      tf.flush()

      self._makeRecipe({'storage-path': tf.name}).install()
      passwd = self.buildout["random"]["passwd"]
      self.assertEqual(passwd, 'secret')
      tf.flush()
      with open(tf.name) as f:
        self.assertEqual(json.load(f), {'': 'secret'})

    self._makeRecipe({'storage-path': tf.name}, "another").install()
    self.assertEqual(self.buildout["another"]["passwd"], passwd)

  def test_bytes(self):
    self._makeRecipe({'bytes': '32'}).install()
    passwd = self.buildout["random"]["passwd"]
    self.assertEqual(len(passwd), 32)
    with open(self.buildout["random"]["storage-path"]) as f:
      self.assertEqual(json.load(f), {'': passwd})

  def test_volatile(self):
    self._makeRecipe({})
    options = self.buildout['random']
    self.assertIn('passwd', options)
    options_items = [(k, v) for k, v in options.items() if k != 'passwd']
    copied_options = options.copy()
    self.assertEqual(list(copied_options.items()), options_items)

  def test_passlib(self):
    recipe = self._makeRecipe({})

    hashed = self.buildout['random']['passwd-sha256-crypt']
    self.assertTrue(
      passlib.hash.sha256_crypt.verify(
        self.buildout['random']['passwd'], hashed))

    hashed = self.buildout['random']['passwd-md5-crypt']
    self.assertTrue(
      passlib.hash.md5_crypt.verify(
        self.buildout['random']['passwd'], hashed))

    hashed = self.buildout['random']['passwd-bcrypt']
    self.assertTrue(
      passlib.hash.bcrypt.verify(
        self.buildout['random']['passwd'], hashed))

    hashed = self.buildout['random']['passwd-ldap-salted-sha1']
    self.assertTrue(
      passlib.hash.ldap_salted_sha1.verify(
        self.buildout['random']['passwd'], hashed))

    with self.assertRaises(zc.buildout.buildout.MissingOption):
      self.buildout['random']['passwd-unknown']
    with self.assertRaises(zc.buildout.buildout.MissingOption):
      self.buildout['random']['unknown']

    copied_options = self.buildout['random'].copy()
    self.assertEqual(list(copied_options.keys()), ['storage-path'])

    recipe.install()
    # when buildout runs again, the values are read from the storage
    # and even the hashed values are the same
    self._makeRecipe({'storage-path': self.buildout['random']['storage-path']}, 'reread')
    self.assertEqual(
      self.buildout['reread']['passwd'],
      self.buildout['random']['passwd'])
    self.assertEqual(
      self.buildout['reread']['passwd-sha256-crypt'],
      self.buildout['random']['passwd-sha256-crypt'])
    self.assertEqual(
      self.buildout['reread']['passwd-bcrypt'],
      self.buildout['random']['passwd-bcrypt'])
    self.assertEqual(
      self.buildout['reread']['passwd-ldap-salted-sha1'],
      self.buildout['random']['passwd-ldap-salted-sha1'])
    # values are strings which is important for python2
    self.assertIsInstance(self.buildout['reread']['passwd'], str)
    self.assertIsInstance(self.buildout['reread']['passwd-ldap-salted-sha1'], str)

  def test_passlib_input_passwd(self):
    self._makeRecipe({'passwd': 'insecure'})
    self.assertEqual(self.buildout['random']['passwd'], 'insecure')

    hashed = self.buildout['random']['passwd-sha256-crypt']
    self.assertTrue(passlib.hash.sha256_crypt.verify('insecure', hashed))
