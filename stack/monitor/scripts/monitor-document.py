#!/usr/bin/env python

import sys
import os
import re
import json
import argparse
import subprocess
from datetime import datetime
import time


def parseArguments():
  """
  Parse arguments for monitor instance.
  """
  parser = argparse.ArgumentParser()
  parser.add_argument('--config_folder',
                      help='Path where json configuration/document will be read and write')
  parser.add_argument('--htpasswd_bin',
                      help='Path apache htpasswd binary. Needed to write htpasswd file.')
  parser.add_argument('--output_cfg_file',
                      help='Ouput parameters in cfg file.')

  return parser.parse_args()

def fileWrite(file_path, content):
  if os.path.exists(file_path):
    try:
      with open(file_path, 'w') as wf:
        wf.write(content)
        return True
    except OSError, e:
      print "ERROR while writing changes to %s.\n %s" % (file_path, str(e))
  return False

def htpasswdWrite(htpasswd_bin,  parameter_dict, value):
  if not os.path.exists(parameter_dict['file']):
    return False
  command = [htpasswd_bin, '-cb', parameter_dict['htpasswd'], parameter_dict['user'], value]
  process = subprocess.Popen(
    command,
    stdin=None,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
  )
  result = process.communicate()[0]
  if process.returncode != 0:
    print result
    return False
  with open(parameter_dict['file'], 'w') as pfile:
    pfile.write(value)
  return True

def httpdCorsDomainWrite(httpd_cors_file, httpd_gracefull_bin, cors_domain):
  cors_string = ""
  cors_domain_list = cors_domain.split()
  old_httpd_cors_file = os.path.join(
    os.path.dirname(httpd_cors_file),
    'prev_%s' % os.path.basename(httpd_cors_file)
  )
  if os.path.exists(old_httpd_cors_file) and os.path.isfile(old_httpd_cors_file):
    try:
      with open(old_httpd_cors_file, 'r') as cors_file:
        if cors_file.read() == cors_domain:
          return True
    except OSError, e:
      print "Failed to open file at %s. \n%s" % (old_httpd_cors_file, str(e))
  for domain in cors_domain_list:
    if cors_string:
      cors_string += '|'
    cors_string += re.escape(domain)
  try:
    with open(httpd_cors_file, 'w') as file:
      file.write('SetEnvIf Origin "^http(s)?://(.+\.)?(%s)$" origin_is=$0\n' % cors_string)
      file.write('Header always set Access-Control-Allow-Origin %{origin_is}e env=origin_is')
  except OSError, e:
    print "ERROR while writing CORS changes to %s.\n %s" % (httpd_cors_file, str(e))
    return False

  # Save current cors domain list
  try:
    with open(old_httpd_cors_file, 'w') as cors_file:
      cors_file.write(cors_domain)
  except OSError, e:
    print "Failed to open file at %s. \n%s" % (old_httpd_cors_file, str(e))
    return False

  # Restart httpd process
  try:
    subprocess.call(httpd_gracefull_bin)
  except OSError, e:
    print "Failed to execute command %s.\n %s" % (httpd_gracefull_bin, str(e))
    return False

def applyEditChage(parser):
  parameter_tmp_file = os.path.join(parser.config_folder, 'config.tmp.json')
  config_file = os.path.join(parser.config_folder, 'config.json')
  parameter_config_file = os.path.join(parser.config_folder, 'config.parameters.json')
  if not os.path.exists(parameter_tmp_file) or not os.path.isfile(parameter_tmp_file):
    return {}
  if not os.path.exists(config_file):
    print "ERROR: Config file doesn't exist... Exiting"
    return {}

  new_parameter_list = []
  parameter_list = []
  description_dict = {}
  result_dict = {}

  try:
    with open(parameter_tmp_file) as tmpfile:
      new_parameter_list = json.loads(tmpfile.read())
  except ValueError:
    print "Error: Couldn't parse json file %s" % parameter_tmp_file

  with open(parameter_config_file) as tmpfile:
    description_dict = json.loads(tmpfile.read())

  for i in range(0, len(new_parameter_list)):
    key = new_parameter_list[i]['key']
    if key != '':
      description_entry = description_dict[key]
      if description_entry['type'] == 'file':
        result_dict[key] = fileWrite(description_entry['file'], new_parameter_list[i]['value'])
      elif description_entry['type'] == 'htpasswd':
        result_dict[key] = htpasswdWrite(parser.htpasswd_bin, description_entry, new_parameter_list[i]['value'])
      elif description_entry['type'] == 'httpdcors':
        result_dict[key] = httpdCorsDomainWrite(description_entry['cors_file'], description_entry['gracefull_bin'], new_parameter_list[i]['value'])

  if (parser.output_cfg_file):
    try:
      with open(parser.output_cfg_file, 'w') as pfile:
        pfile.write('[public]\n')
        for parameter in new_parameter_list:
          if parameter['key']:
            pfile.write('%s = %s\n' % (parameter['key'], parameter['value']))
    except OSError, e:
      print "Error failed to create file %s" % parser.output_cfg_file
      pass

  return result_dict

if __name__ == "__main__":
  parser = parseArguments()
  parameter_tmp_file = os.path.join(parser.config_folder, 'config.tmp.json')
  config_file = os.path.join(parser.config_folder, 'config.json')

  # Run 4 times with sleep
  run_counter = 1
  max_runn = 4
  sleep_time = 15

  while True:
    result_dict = applyEditChage(parser)
    if result_dict != {}:
      status = True
      for key in result_dict:
        if not result_dict[key]:
          status = False
    
      if status and os.path.exists(parameter_tmp_file):
        try:
          os.unlink(config_file)
        except OSError, e:
          print "ERROR cannot remove file: %s" % parameter_tmp_file
        else:
          os.rename(parameter_tmp_file, config_file)
    if run_counter == max_runn:
      break
    else:
      run_counter += 1
      time.sleep(sleep_time)








