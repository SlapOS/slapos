#!/usr/bin/env python

import sys
import os
import stat
import subprocess
import threading
import json
import ConfigParser
import traceback
import argparse

def parseArguments():
  """
  Parse arguments for monitor instance.
  """
  parser = argparse.ArgumentParser()
  parser.add_argument('--config_file',
                      default='monitor.cfg',
                      help='Monitor Configuration file')
  parser.add_argument('--promise-folder',
                      action='append', dest='promise_folder_list',
                      default=[],
                      help='The path to get promise executable files')

  parser.add_argument('--public-folder',
                      action='append', dest='public_folder',
                      help='The path of public folder. All files in this folders will have public acess')

  parser.add_argument('--private-folder',
                      action='append', dest='private_folder',
                      help='The path of private folder. All files in this folders will be accessible with password')

  parser.add_argument('--promise-runner',
                      help='The path of promise runner, use to run promise files')

  parser.add_argument('--wrapper-path',
                      help='Path of monitor generated promise scripts files.')

  return parser.parse_args()


def mkdirAll(path):
  try:
    os.makedirs(path)
  except OSError, e:
    if e.errno == os.errno.EEXIST and os.path.isdir(path):
      pass
    else: raise

def softConfigGet(config, *args, **kwargs):
  try:
    return config.get(*args, **kwargs)
  except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
    return None

class Monitoring(object):

  def __init__(self, configuration_file):
    config = self.loadConfig([configuration_file])

    # Set Monitor variables
    self.monitor_hal_json = config.get("monitor", "monitor-hal-json")
    self.title = config.get("monitor", "title")
    self.service_pid_folder = config.get("monitor", "service-pid-folder")
    self.crond_folder = config.get("monitor", "crond-folder")
    self.wraper_folder = config.get("monitor", "wraper-folder")
    self.promise_runner = config.get("monitor", "promise-runner")
    self.promise_folder_list = config.get("monitor", "promise-folder-list").split()
    self.public_folder = config.get("monitor", "public-folder")
    self.private_folder = config.get("monitor", "private-folder")
    self.public_path_list = config.get("monitor", "public-path-list").split()
    self.private_path_list = config.get("monitor", "private-path-list").split()
    self.monitor_url_list = config.get("monitor", "monitor-url-list").split()

    self.promise_dict = {}
    for promise_folder in self.promise_folder_list:
      self.setupPromiseDictFromFolder(promise_folder)

  def loadConfig(self, pathes, config=None):
    if config is None:
      config = ConfigParser.ConfigParser()
    try:
      config.read(pathes)
    except ConfigParser.MissingSectionHeaderError:
      traceback.print_exc()
    return config

  def setupPromiseDictFromFolder(self, folder):
    for filename in os.listdir(folder):
      path = os.path.join(folder, filename)
      if os.path.isfile(path) and os.access(path, os.X_OK):
        self.promise_dict[filename] = {"path": path,
                                  "configuration": ConfigParser.ConfigParser()}

    # get promises configurations
    #for filename in os.listdir(monitor_promise_folder):
    #  path = os.path.join(monitor_promise_folder, filename)
    #  if os.path.isfile(path) and filename[-4:] == ".cfg":
    #    promise_name = filename[:-4]
    #    if promise_name in promise_dict:
    #      loadConfig([path], promise_dict[promise_name]["configuration"])

  def createSymlinksFromConfig(self, destination_folder, source_path_list, service_name=""):
    if destination_folder:
      if source_path_list:
        for path in source_path_list:
          dirname = os.path.join(destination_folder, service_name)
          try:
            mkdirAll(dirname)  # could also raise OSError
            os.symlink(path, os.path.join(dirname, os.path.basename(path)))
          except OSError, e:
            if e.errno != os.errno.EEXIST:
              raise

  def generateMonitorHalJson(self):
    if self.title:
      self.monitor_dict["title"] = self.title
    if self.monitor_url_list:
      self.monitor_dict["_links"] = {"related_monitor": [{"href": url}
                                  for url in self.monitor_url_list]}
    if self.promise_items:
      service_list = []
      for service_name, promise in self.promise_items:
        service_config = promise["configuration"]
        service_dict = {}
        service_dict["id"] = service_name
        service_dict["_links"] = {"status": {"href": "/public/%s.status.json" % service_name}}  # hardcoded
        tmp = softConfigGet(service_config, "service", "title")
        if tmp:
          service_dict["title"] = tmp
        interface_path = os.path.join(self.private_folder, service_name, "interface/index.html")  # hardcoded
        if os.path.isfile(interface_path):
          service_dict["_links"]["interface"] = {"href": "/private/%s/interface/" % service_name}  # hardcoded
        else:
          service_dict["_links"]["interface"] = {"href": "/default-promise-interface.html?service_name=%s" % service_name}  # XXX hardcoded
        service_list.append(service_dict)

      self.monitor_dict["_embedded"] = {"service": service_list}

    with open(self.monitor_hal_json, "w") as fp:
      json.dump(self.monitor_dict, fp)

  def generateServiceCronEntries(self):
    # XXX only if at least one configuration file is modified, then write in the cron
    cron_line_list = []
    for service_name, promise in self.promise_items:
      service_config = promise["configuration"]
      service_status_path = "%s/%s.status.json" % (self.public_folder, service_name)  # hardcoded
      mkdirAll(os.path.dirname(service_status_path))
      command = ("%s %s %s " % (
          self.promise_runner,
          os.path.join(self.service_pid_folder, "%s.pid" % service_name),
          service_status_path,)
        ) + promise["path"]
      cron_line_list.append("%s %s" % (
          softConfigGet(service_config, "service", "frequency") or "* * * * *",
          command.replace("%", "\\%"),
        ))
      wrapper_path = os.path.join(self.wraper_folder, service_name)
      with open(wrapper_path, "w") as fp:
        fp.write("#!/bin/sh\n%s" % command)  # XXX hardcoded, use dash, sh or bash binary!
      os.chmod(wrapper_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IROTH )
    with open(self.crond_folder + "/monitor-promises", "w") as fp:
      fp.write("\n".join(cron_line_list))

  def bootstrapMonitor(self):
    # create symlinks from service configurations
    self.promise_items = self.promise_dict.items()
    for service_name, promise in self.promise_items:
      service_config = promise["configuration"]
      public_path_list = softConfigGet(service_config, "service", "public-path-list")
      private_path_list = softConfigGet(service_config, "service", "private-path-list")
      if public_path_list:
        self.createSymlinksFromConfig(self.public_folder,
                                      public_path_list.split(),
                                      service_name)
      if private_path_list:
        self.createSymlinksFromConfig(self.private_folder,
                                      private_path_list.split(),
                                      service_name)

    # create symlinks from monitor.conf
    self.createSymlinksFromConfig(self.public_folder, self.public_path_list)
    self.createSymlinksFromConfig(self.private_folder, self.private_path_list)

    # generate monitor.json
    self.monitor_dict = {}
    self.generateMonitorHalJson()

    # put promises to a cron file
    self.generateServiceCronEntries()

    return 0



if __name__ == "__main__":
  parser = parseArguments()

  monitor = Monitoring(parser.config_file)
  
  sys.exit(monitor.bootstrapMonitor())
