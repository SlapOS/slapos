#!{{ python_executable }}

htpasswd_executable = "{{ htpasswd_executable }}"
htpasswd_path = "{{ htpasswd_path }}"
password_changed_once_path = "{{ password_changed_once_path }}"

import cgi
import cgitb
import os
import sys

cgitb.enable(display=0)

def sh(args):
  os.system(" ".join(["'" + arg.replace("'", "'\\''") + "'" for arg in args]))

def touch(path):
  open(path, "w").close()

def main():
  form = cgi.FieldStorage()
  password = form["password"].value
  if sh([htpasswd_executable, "-b", htpasswd_path, "admin", password]):
    sys.stdout.write("Status: 500 Internal Server Error\r\n\r\n")
    return 1
  touch(password_changed_once_path)
  sys.stdout.write("Status: 204 No Content\r\n\r\n")
  return 0

if __name__ == "__main__":
  exit(main())
