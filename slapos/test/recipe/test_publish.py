import os
import tempfile
import unittest

from slapos.recipe import publish


class TestFailsafeUninstall(unittest.TestCase):
  """publish_failsafe registers its uninstaller as a zc.buildout.uninstall
  entry point, so buildout calls it as a plain function -- uninstall(name,
  options) -- with no 'self'.
  """
  def _uninstall(self, options):
    # call exactly as buildout does: the entry point resolves to the unbound
    # function and is invoked with (name, options)
    publish.RecipeFailsafe.uninstall('publish', options)

  def test_uninstall_removes_error_status_file(self):
    with tempfile.NamedTemporaryFile(delete=False) as f:
      f.write(b'previous failure')
      error_status_file = f.name
    self.addCleanup(
      lambda: os.path.exists(error_status_file) and os.unlink(error_status_file))
    self._uninstall({'-error-status-file': error_status_file})
    self.assertFalse(os.path.exists(error_status_file))

  def test_uninstall_without_error_status_file(self):
    # nothing to clean, must not raise
    self._uninstall({})

  def test_uninstall_missing_error_status_file(self):
    # error-status-file configured but already gone, must not raise
    self._uninstall({'-error-status-file': '/nonexistent/does-not-exist'})
