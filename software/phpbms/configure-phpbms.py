# -*- coding: utf-8 -*-
import sys
import os
import shutil

def setup(args):
  mysql_port, mysql_host, mysql_user, mysql_password, mysql_database, base_url, htdocs = args
  
  install_php = os.path.join(htdocs, "install")
  shutil.rmtree(install_php, 1)
  
  
if __name__ == '__main__':
  setup(sys.argv[1:])

