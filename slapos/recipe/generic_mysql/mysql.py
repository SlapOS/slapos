import os
import subprocess
import time
import sys
import pytz

def updateMysql(conf):
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
