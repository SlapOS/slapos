import functools
import os
import shutil
import tempfile
import unittest
import zc.buildout.testing


class TestRedis(unittest.TestCase):
  def getConfig(self):
    return {
      'config-file': self.getTempPath('redis.cfg'),
      'pid-file': self.getTempPath('redis.pid'),
      'port': 1234,
      'ipv6': '::1',
      'server-dir': self.getTempPath('srv'),
      'log-file': self.getTempPath('redis.log'),
      'wrapper': self.getTempPath('wrapper'),
      'server-bin': '/path/to/bin/redis-server',
    }

  def setUp(self):
    self.tmp_dir = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.tmp_dir)
    self.getTempPath = functools.partial(os.path.join, self.tmp_dir)

    self.buildout = buildout = zc.buildout.testing.Buildout()
    self.config = self.getConfig()
    buildout['redis'] = self.config

    from slapos.recipe import redis
    self.recipe = redis.Recipe(buildout, "redis", buildout['redis'])

  def test_install(self):
    self.installed = self.recipe.install()
    redis_cfg = self.installed[0]
    self.assertEqual(redis_cfg, self.config['config-file'])
    with open(redis_cfg) as f:
      self.assertIn(self.config['pid-file'], f.read())

    wrapper = self.installed[1]
    self.assertEqual(wrapper, self.getConfig()['wrapper'])
    with open(wrapper) as f:
      self.assertIn('/path/to/bin/redis-server', f.read())


class TestRedisWithUnixSocket(TestRedis):
  def getConfig(self):
    return dict(
      super(TestRedisWithUnixSocket, self).getConfig(),
      unixsocket=self.getTempPath('redis.sock'))


class TestRedisWithPassword(TestRedis):
  def getConfig(self):
    return dict(
      super(TestRedisWithPassword, self).getConfig(), passwd='secret')


class TestRedisWithPromise(TestRedis):
  def getConfig(self):
    return dict(
      super(TestRedisWithPromise, self).getConfig(), **{
        'cli-bin': '/path/to/bin/redis-cli',
        'promise-wrapper': self.getTempPath('promise-wrapper')
      })

  def test_install(self):
    super(TestRedisWithPromise, self).test_install()
    promise_wrapper = self.installed[2]
    self.assertEqual(promise_wrapper, self.getConfig()['promise-wrapper'])
    with open(promise_wrapper) as f:
      self.assertIn('/path/to/bin/redis-cli', f.read())


class TestRedisWithUnixSocketAndPromise(TestRedisWithPromise):
  def getConfig(self):
    return dict(
      super(TestRedisWithUnixSocketAndPromise, self).getConfig(),
      unixsocket=self.getTempPath('redis.sock'))
