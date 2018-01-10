import os, shutil, tempfile, threading, unittest
from slapos.recipe.librecipe import execute, inotify

class TestInotify(unittest.TestCase):

  def setUp(self):
    self.tmp = tempfile.mkdtemp()

  def tearDown(self):
    shutil.rmtree(self.tmp)

  def test_subfiles(self):
    p = lambda x: os.path.join(self.tmp, x)
    def create(name, text):
      a = open(p(name), 'w')
      a.write(text)
      a.flush()
      return a
    def check(name, text):
      path = next(notified)
      self.assertEqual(path, p(name))
      with open(path) as f:
        self.assertEqual(f.read(), text)
    a = create('first', 'blah')
    a.write('...')
    notified = inotify.subfiles(self.tmp)
    check('first', 'blah')
    os.link(p(a.name), p('a hard link')) # ignored
    b = create('other', 'hello')
    b.close()
    check('other', 'hello')
    c = create('last', '!!!')
    a.close()
    check('first', 'blah...')
    os.rename(p(a.name), p(b.name))
    check('other', 'blah...')
    c.close()
    check('last', '!!!')

  def test_wait_files_creation(self):
    file_list = (
      'foo',
      'bar',
      'hello/world',
      'hello/world!',
      'a/b/c',
    )
    create = lambda x: open(x, 'w').close()
    p = lambda x: os.path.join(self.tmp, x)
    P = lambda x: p(file_list[x])
    create(P(1))
    os.mkdir(p('hello'))
    os.makedirs(p('a/b'))
    t = threading.Thread(target=execute._wait_files_creation,
                         args=(map(p, file_list),))
    t.daemon = True
    t.start()
    def check():
      t.join(.2)
      self.assertTrue(t.is_alive())
    check()
    for x in P(3), p('a/b/d'), P(0):
      create(x)
    check()
    os.rename(P(3), P(2))
    os.rename(p('a/b/d'), P(4))
    check()
    os.remove(P(1))
    for x in P(3), P(1):
      create(x)
    t.join(10)
    self.assertFalse(t.is_alive())
