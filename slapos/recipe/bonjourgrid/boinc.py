# -*- coding: utf-8 -*-

import os
import sys
import re
import subprocess
import time
import signal

def startProcess(launch_args, env=None, cwd=None, stdout=subprocess.PIPE):
  process = subprocess.Popen(launch_args, stdout=stdout,
              stderr=subprocess.STDOUT, env=env,
              cwd=cwd)
  result = process.communicate()[0]
  if process.returncode is None or process.returncode != 0:
    raise NameError("Failed to execute executable.\nThe error was: %s" % result)

def joinProject(args, base_cmd):
  """Finish BOINC Client configuration with create account and attach project"""
  project_args = base_cmd + ['--project_attach', args['project_url'],
                      args['key']]
  startProcess(project_args, cwd=args['boinc_install_dir'])


def createAccount(config, base_cmd):
  """Connect to BOINC Master and create an account
  """
  account_args = base_cmd + ['--create_account', config['project_url'],
                             config['email'], config['account_passwd'],
                             config['account_name']]
  startProcess(account_args, cwd=config['boinc_install_dir'])
  account_file = os.path.join(config['boinc_install_dir'], 'create_account.xml')
  key = re.search("<authenticator>([\w\d\._]+)</authenticator>",
                open(account_file, 'r').read()).group(1)
  return key

def runBoinc(config):
  if len(sys.argv) < 2:
    print "Argument Error: uses %s project_url" % sys.argv[0]
    exit(1)
  if type(config) == type(""):
    print "Error: bonjourgrid.xml parsing error, file not exist or corrupted"
    exit(1)
  #XXX Using define values here for Boinc Master URL
  config['project_url'] = sys.argv[1]

  #launch Boinc Client
  boinc = subprocess.Popen([config['boinc_wrapper']],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)

  #Retrieve ipv4 using by Boinc-client in client-configuration
  client_config = os.path.join(config['boinc_install_dir'], 'client_state.xml')
  while not os.path.exists(client_config):
    time.sleep(5)
    print "Search for file '%r'..." % client_config
  time.sleep(10)
  try:
    #Scan client state xml to find client ipv4 adress
    host = re.search("<ip_addr>([\w\d\.:]+)</ip_addr>",
                  open(client_config, 'r').read()).group(1)
    base_cmd = [config['boinc_cmd'], '--host',
                host + ":" + str(config['boinc_rpc_port']),
                '--passwd', config['boinc_passwd']]
  
    #Create Account for current instance on BOINC master
    print "Create account for current client..."
    key = createAccount(config, base_cmd)
    config['key'] = key
    print "Done. The account key is %s" % key
  
    #Attach project to Boinc Master
    print "Attach client to Boinc Master at %s " % config['project_url']
    try:
      joinProject(config, base_cmd)
    except Exception, e:
      print e
    print "Done! Waiting for Boinc Client now..."
  except Exception, e:
    #An error occure!!!
    os.kill(boinc.pid, signal.SIGTERM)
    print e
  #wait for Boinc client execution
  boinc.wait()
