# -*- coding: utf-8 -*-
import sys
import os

def setup(args):
  mysql_port, mysql_host, mysql_user, mysql_password, mysql_database, base_url, htdocs = args
  
  config_php = os.path.join(htdocs, "config.php")
  install_php = os.path.join(htdocs, "install.php")
  install_sql = os.path.join(htdocs, "install.sql")

  os.chmod(config_php, 0444)
  os.remove(install_php)
  os.remove(install_sql)
  
if __name__ == '__main__':
  setup(sys.argv[1:])
