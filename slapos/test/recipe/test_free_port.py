import socket
import sys
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

  def new_recipe(self, **kw):
    from slapos.recipe import free_port
    from slapos.test.utils import makeRecipe
    options = {
      'ip': '127.0.0.1',
    }
    options.update(kw)
    return makeRecipe(
        free_port.Recipe,
        options=options,
        name='free_port')

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


if __name__ == '__main__':
  unittest.main()
