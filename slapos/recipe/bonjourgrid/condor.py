# -*- coding: utf-8 -*-

import os
import sys
import re
import subprocess
import time

def startProcess(launch_args, env=None, cwd=None, stdout=subprocess.PIPE):
  process = subprocess.Popen(launch_args, stdout=stdout,
              stderr=subprocess.STDOUT, env=env,
              cwd=cwd)
  result = process.communicate()[0]
  if process.returncode is None or process.returncode != 0:
    raise NameError("Failed to execute executable.\nThe error was: %s" % result)

def runCondor(config):
  if len(sys.argv) < 2:
    print "Argument Error: uses %s hostname projectname" % sys.argv[0]
    exit(1)
