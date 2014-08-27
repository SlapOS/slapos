# -*- coding: utf-8 -*-
import sys
import os

def setup(args):
  '''
  Freeglobes doesn't put the good url of the application
  this script ensure the url is the good one
  '''
  mysql_port, mysql_host, mysql_user, mysql_password, mysql_database, base_url, htdocs = args
   
  config_file = os.path.join(htdocs, "conf/config.php")
  new_config_file = os.path.join(htdocs, "conf/config_new.php")
  install_dir = os.path.join(htdocs, "install")
  software_url = "$CONFIG['site_url'] = '%s'; " % base_url 
  
  f = open(config_file, 'r')
  f1 = open(new_config_file, 'w+')
  for line in f.readlines():
    if "$CONFIG['site_url']" not in line:
      f1.write(line)
    else:
      f1.write(software_url)
  f.close()
  f1.close()
  
  os.remove(config_file)
  os.rename(new_config_file, config_file)
  os.rename(install_dir, '%s_done' % install_dir)
  
if __name__ == '__main__':
  setup(sys.argv[1:])
