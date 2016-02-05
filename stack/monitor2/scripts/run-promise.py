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

def main():
  if len(sys.argv) < 4:
    print("Usage: %s <pid_path> <output_path> <command> [<name>] [...]" % sys.argv[0])
    return 2
  pid_path=sys.argv[1]
  output_path=sys.argv[2]
  promise_name = history_folder = related_url = ""
  if len(sys.argv) >= 5:
    promise_name = sys.argv[4]
  if len(sys.argv) >= 6:
    related_url = sys.argv[5]
  if len(sys.argv) >= 7:
    history_folder = sys.argv[6]
  if os.path.exists(pid_path):
    with open(pid_path, "r") as pidfile:
      try:
        pid = int(pidfile.read(6))
      except ValueError:
        pid = None
      if pid and os.path.exists("/proc/" + str(pid)):
        print("A process is already running with pid " + str(pid))
        return 1
  start_date = ""
  with open(pid_path, "w") as pidfile:
    process = executeCommand(sys.argv[3:])
    ps_process = psutil.Process(process.pid)
    start_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ps_process.create_time()))
    pidfile.write(str(process.pid))
  
  status_json = generateStatusJsonFromProcess(process, start_date=start_date, title=promise_name)

  # Save the lastest status change date (needed for rss)
  if related_url:
    status_json['_links'] = {"monitor": {"href": related_url}}
  status_json['change-time'] = ps_process.create_time()
  if os.path.exists(output_path):
    with open(output_path) as f:
      last_result = json.loads(f.read())
      if status_json['status'] == last_result['status'] and last_result.has_key('change-time'):
        status_json['change-time'] = last_result['change-time']

  if history_folder:
    updateStatusHistoryFolder(promise_name, output_path, history_folder)
  with open(output_path, "w") as outputfile:
    json.dump(status_json, outputfile)
  os.remove(pid_path)

def updateStatusHistoryFolder(name, status_file, history_folder):
  old_history_list = []
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
    filename = '%s.status.json' % (
      status_dict['start-date'].replace(' ', '_').replace(':', ''))

  copyfile(status_file, os.path.join(history_path, filename))
  # Don't let history foler grow too much, keep 30 files
  file_list = filter(os.path.isfile,
      glob.glob("%s/*.status.json" % history_path)
    )
  file_count = len(file_list)
  if file_count > 30:
    file_list.sort(key=lambda x: os.path.getmtime(x))
    while file_count > 30:
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
