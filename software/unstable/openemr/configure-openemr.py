# -*- coding: utf-8 -*-
import sys
import os

def setup(args):
  '''
  Freeglobes doesn't put the good url of the application
  this script ensure the url is the good one
  '''
  mysql_port, mysql_host, mysql_user, mysql_password, mysql_database, base_url, htdocs = args
   
  htpasswd_file =  os.path.join(htdocs, "sites/default/.htpasswd")
  document_htaccess = os.path.join(htdocs, "sites/default/documents/.htaccess")
  edi_htaccess = os.path.join(htdocs, "sites/default/edi/.htaccess")
  era_htaccess = os.path.join(htdocs, "sites/default/era/.htaccess")

  f1 = open(htpasswd_file, 'w+')
  f1.write("admin:OA9zt069mtqn6") #admin/admin
  f1.close()
  os.chmod(htpasswd_file, 0644)
  
  htaccess_content = "AuthUserFile %ssites/default/.htpasswd\nAuthName “OpenEMR Protected Page”\nAuthType Basic\nRequire valid-user" % htdocs 
  
  for f in [document_htaccess, edi_htaccess, era_htaccess]:
    file  = open(f, 'w+')
    file.write(htaccess_content)
    file.close()
    os.chmod(f, 0644)

if __name__ == '__main__':
  setup(sys.argv[1:])
