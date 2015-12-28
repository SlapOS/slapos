#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import subprocess
import json

def main():
  if len(sys.argv) < 4:
    print("Usage: %s <pid_path> <output_path> <command...>" % sys.argv[0])
    return 2
  pid_path=sys.argv[1]
  output_path=sys.argv[2]
  if os.path.exists(pid_path):
    with open(pid_path, "r") as pidfile:
      try:
        pid = int(pidfile.read(6))
      except ValueError:
        pid = None
      if pid and os.path.exists("/proc/" + str(pid)):
        print("A process is already running with pid " + str(pid))
        return 1
  with open(pid_path, "w") as pidfile:
    process = executeCommand(sys.argv[3:])
    pidfile.write(str(process.pid))
  status_json = generateStatusJsonFromProcess(process)
  with open(output_path, "w") as outputfile:
    json.dump(status_json, outputfile)
  os.remove(pid_path)


def generateStatusJsonFromProcess(process):
  stdout, stderr = process.communicate()
  try:
    status_json = json.loads(stdout)
  except ValueError:
    status_json = {}
  if process.returncode != 0:
    status_json["status"] = "error"
  elif not status_json.get("status"):
    status_json["status"] = "OK"
  if stderr:
    status_json["error"] = stderr
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
