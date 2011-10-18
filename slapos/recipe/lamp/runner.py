import os
import time
import sys
import shutil
import MySQLdb
    
def executeRunner(args):
    delete, rename, token, mysql_config, script_data = args
    timeout = 5;
    while True:
        if not checkAction(token, mysql_config):
            print "Waiting for 3s and retrying"
            time.sleep(3)
            continue
        time.sleep(timeout)
        for path in delete:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        for data in rename:
            os.rename(data['old'], data['new'])
        if script_data != {}:
            script = script_data['script']
            if os.path.exists(script):
                import subprocess
                #run python script with predefined data
                return_code = subprocess.call([sys.executable, script, script_data['base_url'],
                                 script_data['htdocs'], script_data['renamed'], 
                                 mysql_config['mysql_user'], mysql_config['mysql_password'], 
                                 mysql_config['mysql_database'], mysql_config['mysql_host']])
                if return_code != 0:
                    print "Execution of script %r failed with code: %s" % (script, return_code)
        return

def checkAction(token, mysql_config):
    if type(token) is dict:
        try:
            conn = MySQLdb.connect (host = mysql_config['mysql_host'],
                              port = int(mysql_config['mysql_port']),
                              user = mysql_config['mysql_user'],
                              passwd = mysql_config['mysql_password'],
                              db = mysql_config['mysql_database'])
        except:
            #Mysql is not ready yet?...
            return False
        if token['table'] == "**":
            #only detect if mysql has been started
            conn.close()
            return True
        cursor = conn.cursor ()
        cursor.execute("SHOW TABLES LIKE '%" + token['table'] + "'") #Check if table has been created
        row = cursor.fetchone ()
        if row == None:
            conn.close()
            return False
        else:
            token['table'] = row[0]
        cursor.execute ("SELECT * FROM " + token['table'] + " WHERE " + token['constraint'])
        row = cursor.fetchone ()
        conn.close()
        if row == None:
            return False
        else:
            return True
    else:
        return os.path.exists(token)