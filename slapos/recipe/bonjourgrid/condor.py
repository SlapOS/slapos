# -*- coding: utf-8 -*-

import os
import sys
import re
import subprocess
import time

def writeFile(file, content):
  f = open(file, 'w')
  f.write(content)
  f.close()

def updateCondorConfig(path, path_local, hostname, ipv6):
  """Replace Static information into condor_config and condor_config.local files"""  
  #replace condor host into condor_config
  text = open(path, 'r').read()
  text = re.sub(r'\[%s\]' % ipv6, hostname, text, flags=re.IGNORECASE)
  writeFile(path, text)
  #replace condor host into condor_config.local
  text = open(path_local, 'r').read()
  text = re.sub(r'\[%s\]' % ipv6, hostname, text, flags=re.IGNORECASE)
  writeFile(path_local, text)
  
def updateCondorWrapper(folder, hostname, ipv6):
  """Replace slapos generated value by the true value"""
  for file in os.listdir(folder):
    path = os.path.join(folder, file)
    if os.path.exists(path) and not os.path.isdir(path):
      text = re.sub(r'\[%s\]' % ipv6, hostname, open(path, 'r').read(),
                      flags=re.IGNORECASE)
      writeFile(path, text)

def runCondor(config):
  if len(sys.argv) < 2:
    print "Argument Error: uses %s hostname" % sys.argv[0]
    exit(1)
    
  hostname = sys.argv[1]
  updateCondorConfig(config['condor_config'], config['condor_config_local'],
              hostname, config['ipv6'])
  updateCondorWrapper(config['condor_bin'], hostname, config['ipv6'])
  updateCondorWrapper(config['condor_sbin'], hostname, config['ipv6'])
    
  #launch Boinc Client
  condor = subprocess.Popen([config['condor_wrapper']],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
  condor.wait()
