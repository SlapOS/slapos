# -*- coding: utf-8 -*-
import sys
import os
import MySQLdb

def setup(args):
   renamed, mysql_host,  mysql_user, mysql_password, mysql_database, base_url, htdocs = args
   #base_url, htdocs, renamed, mysql_user, mysql_password, mysql_database, mysql_host = args
   sql_file = os.path.join(htdocs, "scripts/phpfin.sql")
   try:
       conn = MySQLdb.connect (host = mysql_host,
                             user = mysql_user,
                             passwd = mysql_password,
                             db = mysql_database)
       cursor = conn.cursor ()
       with open(sql_file, 'r') as f:
         sql_script = f.read()
         cursor.execute(sql_script)
       conn.close()
   except:
       return

if __name__ == '__main__':
   setup(sys.argv[1:])

