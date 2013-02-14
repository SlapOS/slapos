import sys
import os
import fileinput

def setup(args):
    mysql_port, mysql_host, mysql_user, mysql_password, mysql_database, base_url, htdocs = args

    admin_dir = "admin-" + mysql_user
    admin_include_file = os.path.join(htdocs, admin_dir + "/includes/configure.php")
    searchPattern = "/admin"
    replacePattern =  "/" + admin_dir
    os.chmod(admin_include_file, 0744)
    for line in fileinput.input(admin_include_file, inplace=1):
        if searchPattern in line:
            line = line.replace(searchPattern, replacePattern)
        sys.stdout.write(line)
    os.chmod(admin_include_file, 0444)

if __name__ == '__main__':
    setup(sys.argv[1:])
