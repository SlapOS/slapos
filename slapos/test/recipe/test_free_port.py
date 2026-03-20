import os
import socket
import sys
import tempfile
import textwrap
import unittest

from mock import patch

class SocketMock():
  def __init__(self, *args, **kw):
    self.args = args
    self.kw = kw
    pass

  def nothing_happen(self, *args, **kw):
    pass

  bind = close = nothing_happen

def useMock(function):
  def withMock(function):
    with patch('slapos.recipe.free_port.socket.socket', new=SocketMock):
      return function
  return withMock

class FreePortTest(unittest.TestCase):
  def setUp(self):
    SocketMock.bind = SocketMock.close = SocketMock.nothing_happen

  def new_recipe(self, buildout=None, **kw):
    from slapos.recipe import free_port
    from slapos.test.utils import makeRecipe
    options = {
      'ip': '127.0.0.1',
    }
    options.update(kw)
    default_buildout = {'buildout': {'installed': ''}}
    if buildout:
      for section, opts in buildout.items():
        default_buildout.setdefault(section, {}).update(opts)
    return makeRecipe(
        free_port.Recipe,
        options=options,
        name='free_port',
        buildout=default_buildout)

  @useMock
  def test_ifNoBusyPortThenMinPortIsAlwaysReturned(self):
    recipe = self.new_recipe(minimum=2000)
    self.assertEqual(recipe.options['port'], '2000')

  @useMock
  def test_iterateUntilFreePortIsFound(self):
    def bindFailExceptOnPort2020(socket_instance, binding):
      ip, port = binding
      if port != 2020:
        raise socket.error()
    SocketMock.bind = bindFailExceptOnPort2020
    recipe = self.new_recipe(minimum=2000)
    self.assertEqual(recipe.options['port'], '2020')

  @useMock
  def test_returnsPort0IfNoPortIsFreeInRange(self):
    def bindAlwaysFail(socket_instance, binding):
      raise socket.error()
    SocketMock.bind = bindAlwaysFail
    recipe = self.new_recipe(minimum=2000, maximum=2100)
    self.assertEqual(recipe.options['port'], '0')

  def test_reusesPortFromInstalledFile(self):
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False)
    try:
      f.write(textwrap.dedent("""\
        [free_port]
        port = 4242
        """))
      f.close()
      with patch('slapos.recipe.free_port.socket.socket', new=SocketMock):
        recipe = self.new_recipe(
          minimum=2000,
          buildout={'buildout': {'installed': f.name}},
        )
      self.assertEqual(recipe.options['port'], '4242')
    finally:
      os.unlink(f.name)


if __name__ == '__main__':
  unittest.main()
