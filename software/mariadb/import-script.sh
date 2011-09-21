#!%(bash_binary)s

# Didn't we already restore the database ?
[ -f %(lock_file)r ] && exit 127
touch %(lock_file)r

dbname=db
# Wait for MySQL to be started
while ! %(mysql_binary)r --socket=%(mysql_socket)r -u root -e "use $dbname;"
do
    sleep 5
done

# Restore dump
%(duplicity_binary)r restore --no-encryption %(parameter_remote_backup)r %(local_directory)r
zcat %(dump_name)r | %(mysql_binary)r --socket=%(mysql_socket)r -D $dbname -u root
