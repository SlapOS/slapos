# -*- coding: utf-8 -*-
import sys
import os
import shutil

def setup(args):
  mysql_port, mysql_host, mysql_user, mysql_password, mysql_database, base_url, htdocs = args
  
  install_php = os.path.join(htdocs, "install")
  shutil.rmtree(install_php, 1)
  mod_api = os.path.join(htdocs, "modules/api/install")
  shutil.rmtree(mod_api, 1)
  mod_bms = os.path.join(htdocs, "modules/bms/install")
  shutil.rmtree(mod_bms, 1)
  mod_mailchimp = os.path.join(htdocs, "modules/mailchimp/install")
  shutil.rmtree(mod_mailchimp, 1)
  mod_recurringinvoices = os.path.join(htdocs, "modules/recurringinvoices/install")
  shutil.rmtree(mod_recurringinvoices, 1)
  mod_sample = os.path.join(htdocs, "modules/sample/install")
  shutil.rmtree(mod_sample, 1)

if __name__ == '__main__':
  setup(sys.argv[1:])

