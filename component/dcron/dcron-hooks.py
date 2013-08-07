import os
import shutil
def post_make_hook(options, buildout):
  crontab_path = os.path.join(options['location'], 'bin', 'crontab')
  os.chmod(crontab_path, 0750)
