
# import fnmatch
import grp
import os
import pprint
import pwd
import re
import shutil
import sys

class FileModifier:
  def __init__(self, filename):
    self.filename = filename
    f = open(filename, 'rb')
    self.content = f.read()
    f.close()
  
  def modify(self, key, value):
    (self.content, count) = re.subn(
      r'(<parameter[^>]*\sname\s*=\s*"' + re.escape(key) + r'"[^>]*\sdefault\s*=\s*")[^"]*',
      r"\g<1>" + value,
      self.content)
    return count
      
  def save(self):
    f = open(self.filename, 'w')
    f.write(self.content)
    f.close()


def pre_configure_hook(options, bo, env):
  location = options['location']

  # TODO: double-check which one of these values must be set
  # at instantiation time!

  fm = FileModifier('conf/Config.xml')
  fm.modify('apache_user',  pwd.getpwuid(os.getuid())[0])
  fm.modify('apache_group', grp.getgrgid(os.getgid())[0])
  mioga_base = os.path.join(location, 'var', 'lib', 'Mioga2')
  fm.modify('install_dir', mioga_base)
  fm.modify('tmp_dir', os.path.join(mioga_base, 'tmp'))
  fm.modify('search_tmp_dir', os.path.join(mioga_base, 'mioga_search'))
  fm.modify('maildir', os.path.join(location, 'var', 'spool', 'mioga', 'maildir'))
  fm.modify('maildirerror', os.path.join(location, 'var', 'spool', 'mioga', 'error'))
  fm.modify('mailfifo', os.path.join(location, 'var', 'spool', 'mioga', 'fifo'))
  fm.save()

  # TODO: mail settings are certainly wrong, what is the domain name?



def post_make_hook(options, buildout):
  # location = options['location']
  # print "Mioga - postmakehook"
  # print "We are currently in", os.getcwd()
  # shutil.move("var", location)
  return None
