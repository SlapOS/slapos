import errno
import functools
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

from slapos.recipe import wrapper
from slapos.test.utils import makeRecipe


class WrapperTestCase(unittest.TestCase):
  def getOptions(self):
    raise NotImplementedError()

  def setUp(self):
    self.buildout_directory = tempfile.mkdtemp()
    self.addCleanup(shutil.rmtree, self.buildout_directory)
    self.getTempPath = functools.partial(os.path.join, self.buildout_directory)

    self.wrapper_path = self.getTempPath('wrapper')

    self.recipe = makeRecipe(
      wrapper.Recipe,
      options=self.getOptions(),
      name="wrapper",
      buildout={'buildout': {
        'directory': self.buildout_directory,
      }})

  def terminate_process(self, process):
    try:
      process.terminate()
    except OSError as e:
      if e.errno != errno.ESRCH:
        raise
    process.wait()


class TestSimpleCommandLineWrapper(WrapperTestCase):
  def getOptions(self):
    return {
      'command-line': 'echo hello world',
      'wrapper-path': self.wrapper_path,
    }

  def test_install_and_execute(self):
    installed = self.recipe.install()
    self.assertEqual(installed, self.wrapper_path)
    self.assertEqual(
      subprocess.check_output(installed, universal_newlines=True),
      'hello world\n')


class TestEscapeCommandLine(WrapperTestCase):
  def getOptions(self):
    return {
      'command-line': "echo esca $PE",
      'wrapper-path': self.wrapper_path,
    }

  def test_install_and_execute(self):
    installed = self.recipe.install()
    self.assertEqual(installed, self.wrapper_path)
    self.assertEqual(
      subprocess.check_output(installed, universal_newlines=True),
      "esca $PE\n")


class TestEnvironment(WrapperTestCase):
  def getOptions(self):
    return {
      'command-line': 'sh -c "echo $FOO"',
      'wrapper-path': self.wrapper_path,
      'environment': 'FOO=bar',
    }

  def test_install_and_execute(self):
    installed = self.recipe.install()
    self.assertEqual(installed, self.wrapper_path)

    output = subprocess.check_output(
      installed, universal_newlines=True, env={'FOO': 'foo'})
    self.assertEqual(output, 'bar\n')


class TestHashFiles(WrapperTestCase):
  def getOptions(self):
    hashed_file = self.getTempPath('hashed_file')
    with open(hashed_file, 'w') as f:
      f.write('hello world')
    return {
      'command-line': "cat " + hashed_file,
      'wrapper-path': self.wrapper_path,
      'hash-files': hashed_file
    }

  def test_install_and_execute(self):
    installed = self.recipe.install()
    # 83af3240d992b2165abbd245a3e43368 is hashlib.md5(b'11\nhello world').hexdigest()
    self.assertEqual(
      installed, self.wrapper_path + '-83af3240d992b2165abbd245a3e43368')
    self.assertEqual(
      subprocess.check_output(installed, universal_newlines=True),
      "hello world")


class TestPidFile(WrapperTestCase):
  def getOptions(self):
    self.pidfile = self.getTempPath('hello.pid')
    return {
      'command-line': "/bin/sleep 10",
      'wrapper-path': self.wrapper_path,
      'pidfile': self.pidfile
    }

  def test_install_and_execute(self):
    installed = self.recipe.install()
    self.assertEqual(installed, self.wrapper_path)
    process = subprocess.Popen(
      installed,
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
      universal_newlines=True,
    )
    self.addCleanup(self.terminate_process, process)
    if process.poll():
      self.fail(process.stdout.read())

    for _ in range(20):
      time.sleep(0.1)
      if os.path.exists(self.pidfile):
        break
    else:
      self.fail(process.stdout.read())

    with open(self.pidfile) as f:
      pid = int(f.read())
    self.assertEqual(process.pid, pid)

    with self.assertRaises(subprocess.CalledProcessError) as ctx:
      subprocess.check_output(
        installed, stderr=subprocess.STDOUT, universal_newlines=True)
    self.assertEqual(
      ctx.exception.output, 'Already running with pid %s.\n' % pid)

  def test_stale_pidfile_is_ignored(self):
    installed = self.recipe.install()
    self.assertEqual(installed, self.wrapper_path)
    with open(self.pidfile, 'w') as f:
      f.write('1234')

    process = subprocess.Popen(
      installed,
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
      universal_newlines=True,
    )
    self.addCleanup(self.terminate_process, process)
    if process.poll():
      self.fail(process.stdout.read())

    for _ in range(20):
      time.sleep(0.1)
      with open(self.pidfile) as f:
        pid = int(f.read())
      if process.pid == pid:
        break
    else:
      self.fail('pidfile not updated: %s' % process.stdout.read())


class TestWaitForFiles(WrapperTestCase):
  env = None
  if sys.platform.startswith("linux"):
    expected_output = 'done\n'
  else:
    expected_output = 'Error using inotify, falling back to polling\ndone\n'

  def getOptions(self):
    self.waitfile = self.getTempPath('wait')
    return {
      'command-line': "/bin/echo done",
      'wrapper-path': self.wrapper_path,
      'wait-for-files': self.waitfile,
    }

  def test_install_and_execute(self):
    installed = self.recipe.install()
    self.assertEqual(installed, self.wrapper_path)

    process = subprocess.Popen(
      installed,
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
      universal_newlines=True,
      env=self.env,
    )
    self.addCleanup(self.terminate_process, process)
    if process.poll():
      self.fail(process.stdout.read())

    # nothing happens when file is not there
    for _ in range(10):
      time.sleep(0.1)
      if process.poll():
        self.fail(process.stdout.read())

    open(self.waitfile, 'w').close()
    for _ in range(20):
      time.sleep(0.1)
      if process.poll() is not None:
        self.assertEqual(process.stdout.read(), self.expected_output)
        self.assertEqual(process.returncode, 0)
        break
    else:
      self.fail('process did not start after file was created')


@unittest.skipUnless(
  sys.platform.startswith("linux") and platform.libc_ver()[0] == "glibc" and platform.libc_ver()[1] < '2.34',
  "Inotify is linux only and test only runs on old glibc")
class TestWaitForFilesInotifyError(TestWaitForFiles):

  def setUp(self):
    super(TestWaitForFilesInotifyError, self).setUp()
    # use LD_PRELOAD to inject errors into inotify_add_watch calls
    inotify_mock_c = self.getTempPath('inotify_mock.c')
    inotify_mock_o = self.getTempPath('inotify_mock.o')
    inotify_mock_so = self.getTempPath('inotify_mock.so')
    with open(inotify_mock_c, 'w') as f:
      f.write('''
        #include <sys/inotify.h>
        #include <string.h>
        #include <errno.h>

        int inotify_add_watch(int fd, const char *pathname, uint32_t mask) {
          errno = ENOSPC;
          return -1;
        }

        /* This is a bit tricky because inotify_simple calls
        inotify_add_watch with ctypes.CDLL("libc.so"), which uses
        dlopen("libc.so") and dlsym("inotify_add_watch"), so we first
        override dlsym to return our own inotify_add_watch.
        https://github.com/chrisjbillington/inotify_simple/blob/55737898/inotify_simple.py#L110
        */
        extern void *__libc_dlsym (void *, const char *);
        void *dlsym(void *handle, const char *symbol) {
          if (strcmp(symbol, "inotify_add_watch") == 0) {
            return (void *)inotify_add_watch;
          }
          return (void *)__libc_dlsym(handle, symbol);
        }
        ''')
    subprocess.check_call(['gcc', '-c', '-fPIC', '-o', inotify_mock_o, inotify_mock_c])
    subprocess.check_call(['gcc', '-shared', '-o', inotify_mock_so, inotify_mock_o])
    self.env = dict(
      os.environ,
      PYTHONUNBUFFERED='1',
      LD_PRELOAD=inotify_mock_so)

  expected_output = 'Error using inotify, falling back to polling\ndone\n'


class TestPrivateTmpFS(WrapperTestCase):
  def getOptions(self):
    self.tmpdir = self.getTempPath('tmpdir')
    self.tmpfile = self.getTempPath('tmpdir', 'file')
    self.program = self.getTempPath('program')
    with open(self.program, 'w') as f:
      f.write(
        textwrap.dedent(
          '''\
          #!{sys_executable}
          import os
          with open({tmpfile!r}, 'w') as f:
            f.write('ok')
          with open({tmpfile!r}, 'r') as f:
            print(f.read())
        ''').format(sys_executable=sys.executable, tmpfile=self.tmpfile))
    os.chmod(self.program, 0o700)
    return {
      'command-line': self.program,
      'wrapper-path': self.wrapper_path,
      'private-tmpfs': '1000 ' + self.tmpdir
    }

  def test_install_and_execute(self):
    installed = self.recipe.install()
    self.assertEqual(installed, self.wrapper_path)

    output = subprocess.check_output(
      installed,
      universal_newlines=True,
    )
    self.assertEqual(output, 'ok\n')
    self.assertFalse(os.path.exists(self.tmpfile))


class TestReserveCPU(WrapperTestCase):
  def getOptions(self):
    self.slapos_cpu_exclusive = self.getTempPath('.slapos-cpu-exclusive')
    self.program = self.getTempPath('program')
    with open(self.program, 'w') as f:
      f.write(
        textwrap.dedent(
          '''\
          #!{sys_executable}
          import os
          with open({slapos_cpu_exclusive!r}, 'r') as f:
            print('ok' if int(f.read()) == os.getpid() else 'error')
        ''').format(
            sys_executable=sys.executable,
            slapos_cpu_exclusive=self.slapos_cpu_exclusive,
          ))
    os.chmod(self.program, 0o700)
    return {
      'command-line': self.program,
      'wrapper-path': self.wrapper_path,
      'reserve-cpu': 'true',
    }

  def test_install_and_execute(self):
    installed = self.recipe.install()
    self.assertEqual(installed, self.wrapper_path)

    output = subprocess.check_output(
      installed,
      universal_newlines=True,
      env={'HOME': self.buildout_directory})
    self.assertEqual(output, 'ok\n')
