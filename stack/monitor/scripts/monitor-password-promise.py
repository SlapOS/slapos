#!/usr/bin/env python

password_changed_once_path = "{{ password_changed_once_path }}"

import os

def main():
  if os.path.exists(password_changed_once_path):
    print('{"status":"OK"}')
    return 0
  print('{"status":"BAD","message":"Password never changed"}')
  return 1

if __name__ == "__main__":
  exit(main())
