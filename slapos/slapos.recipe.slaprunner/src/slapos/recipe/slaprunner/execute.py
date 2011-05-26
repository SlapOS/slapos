import os


def execute(args):
  """Portable execution with process replacement"""
  os.execv(args[0], args)
