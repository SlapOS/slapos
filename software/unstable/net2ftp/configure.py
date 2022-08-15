import sys
import os
import MySQLdb

def setup(args):
    mysql_port, mysql_host, mysql_user, mysql_password, mysql_database, base_url, htdocs = args

    sql_file = os.path.join(htdocs, "create_tables.sql")
    try:
        conn = MySQLdb.connect (host = mysql_host,
                              user = mysql_user,
                              passwd = mysql_password,
                              db = mysql_database)
        cursor = conn.cursor ()
        with open(sql_file, 'r') as f:
            sql_script = f.readline()
            while sql_script != "":
                cursor.execute(sql_script)
                sql_script = f.readline()
        conn.close()
    except:
        return

if __name__ == '__main__':
    setup(sys.argv[1:])
