import subprocess

def executeRunner(arguments, delete, rename, chmod, data):
  """Start the instance configure. this may run a python script, move or/and rename
  file or directory when dondition is filled. the condition may be when file exist or when an entry
  exist into database.
  """
  if delete:
    print "Calling lampconfigure with 'delete' arguments"
    subprocess.call(arguments + delete)
  if rename:
    for parameters in rename:
      print "Calling lampconfigure with 'rename' arguments"
      subprocess.call(arguments + parameters)
  if chmod:
    print "Calling lampconfigure with 'chmod' arguments"
    subprocess.call(arguments + chmod)
  if data:
    print "Calling lampconfigure with 'run' arguments"
    print arguments + data
    subprocess.call(arguments + data)

