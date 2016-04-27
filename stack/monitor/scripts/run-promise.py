#!{{ python }}
# -*- coding: utf-8 -*-

import sys
import os
import subprocess
import json
import psutil
import time
from shutil import copyfile
import glob
import argparse

def parseArguments():
  """
  Parse arguments for monitor collector instance.
  """
  parser = argparse.ArgumentParser()
  parser.add_argument('--pid_path',
                      help='Path where the pid of this process will be writen.')
  parser.add_argument('--output',
                      help='The Path of file where Json result of this promise will be saved.')
  parser.add_argument('--promise_script',
                      help='Promise script to execute.')
  parser.add_argument('--promise_name',
                      help='Title to give to this promise.')
  parser.add_argument('--promise_type',
                      default='status',
                      help='Type of promise to execute. [status, report].')
  parser.add_argument('--monitor_url',
                      help='Monitor Instance website URL.')
  parser.add_argument('--history_folder',
                      help='Path where old result file will be placed before generate a new json result file.')
  parser.add_argument('--instance_name',
                      default='UNKNOWN Software Instance',
                      help='Software Instance name.')
  parser.add_argument('--hosting_name',
                      default='UNKNOWN Hosting Subscription',
                      help='Hosting Subscription name.')

  return parser.parse_args()

def main():
  parser = parseArguments()

  if os.path.exists(parser.pid_path):
    with open(parser.pid_path, "r") as pidfile:
      try:
        pid = int(pidfile.read(6))
      except ValueError:
        pid = None
      if pid and os.path.exists("/proc/" + str(pid)):
        print("A process is already running with pid " + str(pid))
        return 1
  start_date = ""
  with open(parser.pid_path, "w") as pidfile:
    process = executeCommand(parser.promise_script)
    ps_process = psutil.Process(process.pid)
    start_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ps_process.create_time()))
    pidfile.write(str(process.pid))

  status_json = generateStatusJsonFromProcess(process, start_date=start_date)

  status_json['_links'] = {"monitor": {"href": parser.monitor_url}}
  status_json['title'] = parser.promise_name
  status_json['instance'] = parser.instance_name
  status_json['hosting_subscription'] = parser.hosting_name

  # Save the lastest status change date (needed for rss)
  status_json['change-time'] = ps_process.create_time()
  if os.path.exists(parser.output):
    with open(parser.output) as f:
      last_result = json.loads(f.read())
      if status_json['status'] == last_result['status'] and last_result.has_key('change-time'):
        status_json['change-time'] = last_result['change-time']

  updateStatusHistoryFolder(
    parser.promise_name,
    parser.output,
    parser.history_folder,
    parser.promise_type
  )
  with open(parser.output, "w") as outputfile:
    json.dump(status_json, outputfile)
  os.remove(parser.pid_path)

def updateStatusHistoryFolder(name, status_file, history_folder, promise_type):
  old_history_list = []
  keep_item_amount = 25
  history_path = os.path.join(history_folder, name, '.jio_documents')
  if not os.path.exists(status_file):
    return
  if not os.path.exists(history_folder):
    return
  if not os.path.exists(history_path):
    try:
      os.makedirs(history_path)
    except OSError, e:
      if e.errno == os.errno.EEXIST and os.path.isdir(history_path):
        pass
      else: raise
  with open(status_file, 'r') as sf:
    status_dict = json.loads(sf.read())
    filename = '%s.%s.json' % (
      status_dict['start-date'].replace(' ', '_').replace(':', ''),
      promise_type)

  copyfile(status_file, os.path.join(history_path, filename))
  # Don't let history foler grow too much, keep xx files
  file_list = filter(os.path.isfile,
      glob.glob("%s/*.%s.json" % (history_path, promise_type))
    )
  file_count = len(file_list)
  if file_count > keep_item_amount:
    file_list.sort(key=lambda x: os.path.getmtime(x))
    while file_count > keep_item_amount:
      to_delete = file_list.pop(0)
      try:
        os.unlink(to_delete)
        file_count -= 1
      except OSError:
        raise

def generateStatusJsonFromProcess(process, start_date=None, title=None):
  stdout, stderr = process.communicate()
  try:
    status_json = json.loads(stdout)
  except ValueError:
    status_json = {}
  if process.returncode != 0:
    status_json["status"] = "ERROR"
  elif not status_json.get("status"):
    status_json["status"] = "OK"
  if stderr:
    status_json["message"] = stderr
  if start_date:
    status_json["start-date"] = start_date
  if title:
    status_json["title"] = title
  return status_json


def executeCommand(args):
  return subprocess.Popen(
    args,
    #cwd=instance_path,
    #env=None if sys.platform == 'cygwin' else {},
    stdin=None,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
  )

if __name__ == "__main__":
  sys.exit(main())
