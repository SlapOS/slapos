import os
import socket
import signal
import shutil
import slapos.slap
import subprocess
import time
import atexit
from erp5testreporthandler import ERP5TestReportHandler

process_group_pid_list = []
def clean():
  for pgpid in process_group_pid_list:
    try:
      os.killpg(pgpid, signal.SIGTERM)
    except:
      pass

def sigterm_handler(signal, frame):
  clean()

def sigint_handler(signal, frame):
  clean()
  raise KeyboardInterrupt

signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGTERM, sigterm_handler)
atexit.register(clean)

def getCurrentBranchName(config, p):
  r = subprocess.Popen([config['git_binary'], 'branch'], stdout=subprocess.PIPE, cwd=p).communicate()[0]
  for f in r.splitlines():
    if f.startswith('*'):
      return f.split()[1]
  return ''

def getRevision(config, p):
  return subprocess.Popen([config['git_binary'], 'rev-parse', 'HEAD'], stdout=subprocess.PIPE, cwd=p).communicate()[0].strip()

def getCurrentFetchRemote(config, p):
  r = subprocess.Popen([config['git_binary'], 'remote', '-v'], stdout=subprocess.PIPE, cwd=p).communicate()[0]
  remote = ''
  for f in r.splitlines():
    if f.startswith('origin') and f.endswith('(fetch)'):
      if remote != '':
        raise ValueError('Too many remotes: %s' % r)
      remote = r.split()[1]
  return remote

def getMachineIdString():
  """Returns machine identification string"""
  kw = dict(stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  idstr = subprocess.Popen(["uname", "-m"], **kw).communicate()[0].strip()

  # try to detect gcc version
  try:
    gcc_list = subprocess.Popen(["gcc", "-v"], **kw).communicate()[0].split(
        '\n')
    for gcc in gcc_list:
      if gcc.startswith('gcc version'):
        idstr += ' gcc:' + gcc.split()[2]
        break
  except IndexError:
    pass

  # try to detect libc version
  try:
    libdir = os.path.sep + 'lib'
    for libso in os.listdir(libdir):
      if libso.startswith('libc.') and os.path.islink(os.path.join(libdir,
        libso)):
        libc = os.readlink(os.path.join(libdir, libso))
        if libc.endswith('.so'):
          idstr += ' libc:' + libc.split('-')[1][:-3]
        else:
          idstr += ' ' + libc
        break
  except IndexError:
    pass

  return idstr

def run(args):
  config = args[0]
  for k,v in config['environment'].iteritems():
    os.environ[k] = v
  proxy = None
  slapgrid = None
  last_revision_file = os.path.join(config['working_directory'],
        'revision.txt')
  if os.path.exists(last_revision_file):
    os.unlink(last_revision_file)
  # fetch repository from git
  repository_clone = os.path.join(config['working_directory'], 'repository')
  profile_path = os.path.join(repository_clone, config['profile_path'])
  if os.path.exists(config['proxy_database']):
    os.unlink(config['proxy_database'])
  proxy = subprocess.Popen([config['slapproxy_binary'],
    config['slapos_config']], close_fds=True, preexec_fn=os.setsid)
  process_group_pid_list.append(proxy.pid)
  slap = slapos.slap.slap()
  slap.initializeConnection(config['master_url'])
  while True:
    try:
      slap.registerSupply().supply(profile_path,
        computer_guid=config['computer_id'])
    except socket.error:
      time.sleep(1)
      pass
    else:
      break
  while True:
    info_list = []
    a = info_list.append
    while True:
      try:
        if os.path.exists(repository_clone):
          if getCurrentFetchRemote(config, repository_clone) != config['repository']:
            shutil.rmtree(repository_clone)
        if not os.path.exists(repository_clone):
          subprocess.check_call([config['git_binary'], 'clone',
            config['repository'], repository_clone])
        # switch to branch
        branch = getCurrentBranchName(config, repository_clone)
        if branch != config['branch']:
          subprocess.check_call([config['git_binary'], 'checkout', '--force',
            '--track', '-b', config['branch'], 'origin/'+config['branch']],
            cwd=repository_clone)
        subprocess.check_call([config['git_binary'], 'pull', '--rebase'],
            cwd=repository_clone)
      except Exception:
        print 'Retrying git in 60s'
        time.sleep(60)
      else:
        break
    a('Tested repository: %s' % config['repository'])
    a('Machine identification: %s' % getMachineIdString())
    erp5_report = ERP5TestReportHandler(config['test_suite_master_url'],
        '@'.join([config['suite_name'], branch]))
    last_revision = ''
    if os.path.exists(last_revision_file):
      last_revision = open(last_revision_file).read().strip()
    revision = getRevision(config, repository_clone)
    open(last_revision_file, 'w').write(revision)
    if revision != last_revision:
      print 'Running for revision %r' % revision
      while True:
        try:
          erp5_report.reportStart()
        except Exception:
          print 'Retrying in 5s'
          time.sleep(5)
        else:
          break
      if os.path.exists(config['software_root']):
        shutil.rmtree(config['software_root'])
      os.mkdir(config['software_root'])
      out_file = os.path.join(config['working_directory'], 'slapgrid.out')
      if os.path.exists(out_file):
        os.unlink(out_file)
      out = open(out_file, 'w')
      begin = time.time()
      slapgrid_environment = os.environ.copy()
      for k, v in config['slapgrid_environment'].iteritems():
        slapgrid_environment[k] = v
      a('Slapgrid environment: %r'% config['slapgrid_environment'])
      slapgrid = subprocess.Popen([config['slapgrid_software_binary'], '-vc',
        config['slapos_config']], close_fds=True, preexec_fn=os.setsid,
        stdout=out, stderr=subprocess.STDOUT, env=slapgrid_environment)
      process_group_pid_list.append(slapgrid.pid)
      slapgrid.communicate()
      out.close()
      while True:
        try:
          erp5_report.reportFinished(out_file,revision,
              slapgrid.returncode == 0, time.time() - begin,
              '\n'.join(info_list))
        except Exception:
          print 'Retrying in 5s'
          time.sleep(5)
        else:
          break
    print 'Sleeping for 600s'
    time.sleep(600)
