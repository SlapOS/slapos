import subprocess

def executeRunner(args):
  """Start the instance configure. this may run a python script, move or/and rename
  file or directory when dondition is filled. the condition may be when file exist or when an entry
  exist into database.
  """
  arguments, delete, rename, chmod, data = args
  if delete != []:
    print "Calling lampconfigure with 'delete' arguments"
    result = subprocess.Popen(arguments + delete)
    result.wait()
  if rename != []:
    for parameters in rename:
      print "Calling lampconfigure with 'rename' arguments"
      result = subprocess.Popen(arguments + parameters)
      result.wait()
  if chmod != []:
    print "Calling lampconfigure with 'chmod' arguments"
    result = subprocess.Popen(arguments + chmod)
    result.wait()
  if data != []:
    print "Calling lampconfigure with 'run' arguments"
    print arguments + data
    result = subprocess.Popen(arguments + data)
    result.wait()
    return

