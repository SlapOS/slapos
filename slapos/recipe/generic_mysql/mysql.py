import os
import subprocess
import time
import sys
import pytz

def updateMysql(mysql_upgrade_binary, mysql_binary, mysql_script_file):
  sleep = 30
  with open(mysql_script_file) as script_file:
    mysql_script = script_file.read()
  mysql_list = mysql_binary, '-B'
  mysql_tzinfo_to_sql_list = (
    os.path.join(os.path.dirname(mysql_binary), 'mysql_tzinfo_to_sql'),
    os.path.join(os.path.dirname(pytz.__file__), 'zoneinfo'),
  )
  while True:
    while True:
      mysql_upgrade = subprocess.Popen(mysql_upgrade_binary,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
      result = mysql_upgrade.communicate()[0]
      if mysql_upgrade.returncode:
        print "Command %r failed with result:\n%s" % (mysql_upgrade_binary, result)
        break
      print "MySQL database upgraded with result:\n%s" % result
      mysql = subprocess.Popen(mysql_list, stdin=subprocess.PIPE,
          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
      result = mysql.communicate(mysql_script)[0]
      if mysql.returncode:
        print 'Command %r failed with:\n%s' % (mysql_list, result)
        break
      # import timezone database
      mysql_tzinfo_to_sql = subprocess.Popen(mysql_tzinfo_to_sql_list, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      timezone_sql = mysql_tzinfo_to_sql.communicate()[0]
      if mysql_tzinfo_to_sql.returncode != 0:
        print 'Command %r failed with:\n%s' % (mysql_tzinfo_to_sql_list, result)
        break
      mysql = subprocess.Popen(mysql_list + ('mysql',), stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
      result = mysql.communicate(timezone_sql)[0]
      if mysql.returncode:
        print 'Command %r failed with:\n%s' % (mysql_list, result)
        break
      print 'SlapOS initialisation script succesfully applied on database.'
      return
    print 'Sleeping for %ss and retrying' % sleep
    sys.stdout.flush()
    sys.stderr.flush()
    time.sleep(sleep)
