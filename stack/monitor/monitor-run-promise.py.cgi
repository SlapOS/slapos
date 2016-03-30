#!{{ python_executable }}
# Put this file in the software release
promise_wrapper_folder = "{{ promise_wrapper_folder }}"

import cgi
import cgitb
import os

cgitb.enable(display=0)

def main():
  form = cgi.FieldStorage()
  promise_name = form["service"].value
  if "/" not in promise_name:
    promise_path = os.path.join(promise_wrapper_folder, promise_name)
    os.spawnl(os.P_NOWAIT, promise_path, promise_path)
  print("Status: 204 No Content\r\n\r")

if __name__ == "__main__":
  exit(main())
