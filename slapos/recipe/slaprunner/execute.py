import os


def execute(args):
  """Portable execution with process replacement"""
  if args.get("path", None):
    os.environ['PATH'] = args["path"]
  os.execv(args["launch_args"][0], args["launch_args"])
