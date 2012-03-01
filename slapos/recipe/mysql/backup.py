import subprocess
import os

# Replace mysqldump | gzip > tmpdump && mv -f tmpdump dumpfile
def do_backup(kwargs):
  mysqldump_cmd = kwargs['mysqldump']
  gzip_bin = kwargs['gzip']
  tmpdump = kwargs['tmpdump']
  dumpfile = kwargs['dumpfile']

  # mysqldump | gzip > tmpdump
  with open(tmpdump, 'w') as output:
    mysqldump = subprocess.Popen(mysqldump_cmd,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
    gzip = subprocess.Popen([gzip_bin],
                            stdin=mysqldump.stdout,
                            stdout=output,
                            stderr=subprocess.STDOUT)
    mysqldump.stdout.close()

    if gzip.wait() != 0:
      raise ValueError("Gzip return a non zero value.")

  os.rename(tmpdump, dumpfile)
