##############################################################################
#
# Copyright (c) 2010 Vifib SARL and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
import logging
import os
import setuptools
import shutil
import subprocess
import tempfile
import zc.buildout

def readElfAsDict(f):
  """Reads ELF information from file"""
  popen = subprocess.Popen(['readelf', '-d', f],
      stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  result = popen.communicate()[0]
  if popen.returncode != 0:
    raise AssertionError(result)
  library_list = []
  rpath_list = []
  runpath_list = []
  for l in result.split('\n'):
    if '(NEEDED)' in l:
      library_list.append(l.split(':')[1].strip(' []'))
    elif '(RPATH)' in l:
      rpath_list = [q.rstrip('/') for q in l.split(':',1)[1].strip(' []').split(':')]
    elif '(RUNPATH)' in l:
      runpath_list = [q.rstrip('/') for q in l.split(':',1)[1].strip(' []').split(':')]
  if len(runpath_list) == 0:
    runpath_list = rpath_list
  elif len(rpath_list) != 0 and runpath_list != rpath_list:
    raise ValueError('RPATH and RUNPATH are different.')
  return dict(
    library_list=sorted(library_list),
    runpath_list=sorted(runpath_list)
  )

def call(*args, **kwargs):
  """Subprocess call with closed file descriptors and stdin"""
  kwargs.update(
    stdin=subprocess.PIPE,
    close_fds=True)
  popen = subprocess.Popen(*args, **kwargs)
  popen.stdin.flush()
  popen.stdin.close()
  popen.stdin = None
  popen.communicate()
  if popen.returncode != 0:
    raise subprocess.CalledProcessError(popen.returncode, ' '.join(args[0]))

def calls(call_string, **kwargs):
  """Subprocesser caller which allows to pass arguments as string"""
  call(call_string.split(), **kwargs)

def guessworkdir(path):
  if len(os.listdir(path)) == 1:
    return os.path.join(path, os.listdir(path)[0])
  return path

class Script:
  """Free script building system"""
  def _checkPromisee(self, location):
    promisee_problem_list = []
    a = promisee_problem_list.append
    for promisee in self.options['slapos_promisee'].split('\n'):
      promisee = promisee.strip()
      if not promisee:
        continue
      if promisee.startswith('file:') or promisee.startswith('statlib'):
        s, path = promisee.split(':')
        if not os.path.exists(os.path.join(location, path)):
          a('File promisee not met for %r' % path)
      elif promisee.startswith('directory'):
        s, path = promisee.split(':')
        if not os.path.isdir(os.path.join(location, path)):
          a('Directory promisee not met for %r' %
              path)
      elif promisee.startswith('dynlib:'):
        if 'linked:' not in promisee:
          raise zc.buildout.UserError('dynlib promisee requires \'linked:\' '
            'parameter.')
        if 'rpath:' not in promisee:
          rpath_list = []
        for promisee_part in promisee.split():
          if promisee_part.startswith('dynlib:'):
            s, path = promisee_part.split(':')
          elif promisee_part.startswith('linked:'):
            s, link_list = promisee_part.split(':')
            link_list = link_list.split(',')
          elif promisee_part.startswith('rpath:'):
            s, rpath_list = promisee_part.split(':')
            if rpath_list:
              r = rpath_list
              rpath_list = []
              for q in r.split(','):
                if q.startswith('!'):
                  q = q.replace('!', location)
                rpath_list.append(q)
            else:
              rpath_list = []
        if not os.path.exists(os.path.join(location, path)):
          a('Dynlib promisee file not met %r' % promisee)
        else:
          elf_dict = readElfAsDict(os.path.join(location, path))
          if sorted(link_list) != sorted(elf_dict['library_list']):
            a('Promisee library list not met (wanted: %r, found: %r)'%(
              link_list, elf_dict['library_list']))
          if sorted(rpath_list) != sorted(elf_dict['runpath_list']):
            a('Promisee rpath list not met (wanted: %r, found: %r)'%(
              rpath_list, elf_dict['runpath_list']))
      else:
        raise zc.buildout.UserError('Unknown promisee %r' % promisee)
    if len(promisee_problem_list):
      raise zc.buildout.UserError('Promisee not met, found issues:\n  %s' %
          '  '.join([q+'\n' for q in promisee_problem_list]))

  def download(self, url, md5sum):
    download = zc.buildout.download.Download(self.buildout['buildout'],
        hash_name=True)
    path, is_temp = download(url, md5sum=self.options.get('md5sum'))
    return path

  def extract(self, path):
    extract_dir = tempfile.mkdtemp(self.name)
    self.logger.debug('Created working directory %r' % extract_dir)
    setuptools.archive_util.unpack_archive(path, extract_dir)
    self.cleanup_dir_list.append(extract_dir)
    return extract_dir

  script = 'raise NotImplementedError'
  def __init__(self, buildout, name, options):
    self.cleanup_dir_list = []
    self.options = options
    self.buildout = buildout
    self.name = name
    self.logger = logging.getLogger('SlapOS build of %s' % self.name)

    self.options.setdefault('location',
        os.path.join(buildout['buildout']['parts-directory'], self.name))

    # cleanup some variables
    for k in ['location', 'url', 'md5sum']:
      self.options[k] = self.options.get(k, '').strip()
    self.options['script'] = self.options.get('script', self.script) % self.options

  def getEnvironment(self):
    # prepare cool dictionary
    wanted_env = {}
    for line in self.options.get('environment', '').splitlines():
      line = line.strip()
      if not line:
        continue
      if not '=' in line:
        raise zc.buildout.UserError('Line %r in environment is incorrect' % line)

      key, value = line.split('=')
      key = key.strip()
      value = value.strip()
      if key in wanted_env:
        raise zc.buildout.UserError('Key %r is repeated' % key)
      wanted_env[key] = value
    env = {}
    for k,v in os.environ.iteritems():
      change = wanted_env.pop(k, None)
      if change is not None:
        env[k] = change % os.environ
        self.logger.info('Environment %r setup to %r' % (k, env[k]))
      else:
        env[k] =v
    for k,v in wanted_env.iteritems():
      self.logger.info('Environment %r added with %r' % (k, v))
      env[k] = v
    return env

  def install(self):
    try:
      env = self.getEnvironment()
      exec self.options['script']
      try:
        self._checkPromisee(self.options['location'])
      except Exception:
        if os.path.exists(self.options['location']):
          self.logger.info('Removing location %r because of error' % self.options['location'])
          shutil.rmtree(self.options['location'])
        raise
    finally:
      for d in self.cleanup_dir_list:
        if os.path.exists(d):
          self.logger.debug('Cleanup directory %r' % d)
          shutil.rmtree(d)

    return [self.options['location']]

  def update(self):
    pass

class Cmmi(Script):
  """Simple configure-make-make-insall compatible with hexagonit.recipe.cmmi

  Compatibility on parameter level, without bug-to-bug, hack-to-hack"""

  script = """
extract_dir = self.extract(self.download(self.options['url'], self.options.get('md5sum')))
workdir = guessworkdir(extract_dir)
configure_command = ["./configure", "--prefix=%(location)s"]
configure_command.extend(%(configure-options)r.split())
self.logger.info('Configuring with: %%s' %% configure_command)
call(configure_command, cwd=workdir, env=env)
self.logger.info('Building')
call("make", cwd=workdir, env=env)
self.logger.info('Installing')
call(["make", "install"], cwd=workdir, env=env)
"""

  def __init__(self, buildout, name, options):
    options['configure-options'] = ' '.join(options.get('configure-options', '').strip().splitlines())
    Script.__init__(self, buildout, name, options)
