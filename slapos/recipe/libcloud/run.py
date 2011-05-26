from os import execl
import sys

def run(server_binary, configuration_file):
  sys.stdout.flush()
  execl(server_binary, server_binary, configuration_file)
