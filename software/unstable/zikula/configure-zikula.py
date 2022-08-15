# -*- coding: utf-8 -*-
import sys
import os
import shutil

def setup(args):
  mysql_port, mysql_host, mysql_user, mysql_password, mysql_database, base_url, htdocs = args
  
  config_php = os.path.join(htdocs, "config/config.php")
  install_php = os.path.join(htdocs, "install.php")
  install_folder = os.path.join(htdocs, "install")
  upgrade_php = os.path.join(htdocs, "upgrade.php")

  os.chmod(config_php, 0444)
  os.remove(install_php)
  os.remove(upgrade_php)
  shutil.rmtree(install_folder)
  
if __name__ == '__main__':
  setup(sys.argv[1:])

