# -*- coding: utf-8 -*-
import sys
import os

def setup(args):
   base_url, htdocs, renamed, mysql_user, mysql_password, mysql_database, mysql_host = args
   os.rename(os.path.join(htdocs, "config.inc.php"), os.path.join(htdocs, "config.php"))
   config_php = os.path.join(htdocs, "config.php")
   os.chmod(config_php, 0444)

if __name__ == '__main__':
   setup(sys.argv[1:])
