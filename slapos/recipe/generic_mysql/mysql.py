import os
import subprocess
import time
import sys
import pytz


def runMysql(args):
  sleep = 60
  conf = args[0]
  mysqld_wrapper_list = [conf['mysqld_binary'], '--defaults-file=%s' %
      conf['configuration_file']]
  # we trust mysql_install that if mysql directory is available mysql was
  # correctly initalised
  if not os.path.isdir(os.path.join(conf['data_directory'], 'mysql')):
    while True:
      # XXX: Protect with proper root password
      # XXX: Follow http://dev.mysql.com/doc/refman/5.0/en/default-privileges.html
      popen = subprocess.Popen([conf['mysql_install_binary'],
        '--defaults-file=%s' % conf['configuration_file'],
        '--skip-name-resolve',
        '--datadir=%s' % conf['data_directory'],
        '--basedir=%s' % conf['mysql_base_directory']],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
      result = popen.communicate()[0]
      if popen.returncode is None or popen.returncode != 0:
        print "Failed to initialise server.\nThe error was: %s" % result
        print "Waiting for %ss and retrying" % sleep
        time.sleep(sleep)
      else:
        print "Mysql properly initialised"
        break
  else:
    print "MySQL already initialised"
  print "Starting %r" % mysqld_wrapper_list[0]
  sys.stdout.flush()
  sys.stderr.flush()
  # try to increase the maximum number of open file descriptors.
  # it seems that mysqld requires (max_connections + 810) file descriptors.
  # to make it possible, you need to set the hard limit of nofile in
  # /etc/security/limits.conf like the following :
  #   @slapsoft hard nofile 2048
  try:
    import resource
    required_nofile = 2048 # XXX hardcoded value more than 1000 + 810
    nofile_limit_list = [max(x, required_nofile) for x in resource.getrlimit(resource.RLIMIT_NOFILE)]
    resource.setrlimit(resource.RLIMIT_NOFILE, nofile_limit_list)
  except ImportError:
    # resource library is only available on Unix platform.
    pass
  except ValueError:
    # 'ValueError: not allowed to raise maximum limit'
    pass
  os.execl(mysqld_wrapper_list[0], *mysqld_wrapper_list)


def updateMysql(args):
  conf = args[0]
  sleep = 30
  is_succeed = False
  try:
    script_filename = conf.pop('mysql_script_file')
  except KeyError:
    pass
  else:
    assert 'mysql_script' not in conf
    with open(script_filename) as script_file:
      conf['mysql_script'] = script_file.read()
  is_succeeded = False
  while True:
    while True:
      mysql_upgrade_list = [conf['mysql_upgrade_binary'], '--user=root']
      if 'socket' in conf:
        mysql_upgrade_list.append('--socket=' + conf['socket'])
      mysql_upgrade = subprocess.Popen(mysql_upgrade_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
      result = mysql_upgrade.communicate()[0]
      if mysql_upgrade.returncode is None:
        mysql_upgrade.kill()
      if mysql_upgrade.returncode == 0:
        print "MySQL database upgraded with result:\n%s" % result
      elif 'is already upgraded' in result:
        print "No need to upgrade MySQL database"
      else:
        print "Command %r failed with result:\n%s" % (mysql_upgrade_list, result)
        break
      mysql_list = [conf['mysql_binary'].strip(), '-B', '--user=root']
      if 'socket' in conf:
        mysql_list.append('--socket=' + conf['socket'])
      mysql = subprocess.Popen(mysql_list, stdin=subprocess.PIPE,
          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
      result = mysql.communicate(conf['mysql_script'])[0]
      if mysql.returncode is None:
        mysql.kill()
      if mysql.returncode != 0:
        print 'Command %r failed with:\n%s' % (mysql_list, result)
        break
      # import timezone database
      mysql_tzinfo_to_sql_binary = os.path.join(
        os.path.dirname(conf['mysql_binary'].strip()), 'mysql_tzinfo_to_sql')
      zoneinfo_directory = '%s/zoneinfo' % os.path.dirname(pytz.__file__)
      mysql_tzinfo_to_sql_list = [mysql_tzinfo_to_sql_binary, zoneinfo_directory]
      mysql_tzinfo_to_sql = subprocess.Popen(mysql_tzinfo_to_sql_list, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      timezone_sql = mysql_tzinfo_to_sql.communicate()[0]
      if mysql_tzinfo_to_sql.returncode != 0:
        print 'Command %r failed with:\n%s' % (mysql_tzinfo_to_sql_list, result)
        break
      mysql = subprocess.Popen(mysql_list + ['mysql',], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
      result = mysql.communicate(timezone_sql)[0]
      if mysql.returncode is None:
        mysql.kill()
      if mysql.returncode != 0:
        print 'Command %r failed with:\n%s' % (mysql_list, result)
        break
      is_succeeded = True
      break
    if is_succeeded:
      print 'SlapOS initialisation script succesfully applied on database.'
      break
    print 'Sleeping for %ss and retrying' % sleep
    sys.stdout.flush()
    sys.stderr.flush()
    time.sleep(sleep)
