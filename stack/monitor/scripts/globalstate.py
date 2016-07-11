#!/usr/bin/env python

import sys
import os
import glob
import json
import ConfigParser
import time
from datetime import datetime

def softConfigGet(config, *args, **kwargs):
  try:
    return config.get(*args, **kwargs)
  except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
    return ""

def generateStatisticsData(stat_file_path, content):
  # csv document for statictics
  if not os.path.exists(stat_file_path):
    with open(stat_file_path, 'w') as fstat:
      data_dict = {
        "date": time.time(),
        "data": ["Date, Success, Error, Warning"]
      }
      fstat.write(json.dumps(data_dict))

  current_state = ''
  if content.has_key('state'):
    current_state = '%s, %s, %s, %s' % (
      content['date'],
      content['state']['success'],
      content['state']['error'],
      content['state']['warning'])

  # append to file
  if current_state:
    with open (stat_file_path, mode="r+") as fstat:
      fstat.seek(0,2)
      position = fstat.tell() -2
      fstat.seek(position)
      fstat.write('%s}' % ',"{}"]'.format(current_state))

def main(args_list):
  monitor_file, instance_file = args_list

  monitor_config = ConfigParser.ConfigParser()
  monitor_config.read(monitor_file)

  base_folder = monitor_config.get('monitor', 'private-folder')
  status_folder = monitor_config.get('monitor', 'public-folder')
  base_url = monitor_config.get('monitor', 'base-url')
  related_monitor_list = monitor_config.get("monitor", "monitor-url-list").split()
  statistic_folder = os.path.join(base_folder, 'data', '.jio_documents')
  parameter_file = os.path.join(base_folder, 'config', '.jio_documents', 'config.json')

  report_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

  if not os.path.exists(statistic_folder):
    try:
      os.makedirs(statistic_folder)
    except OSError, e:
      if e.errno == os.errno.EEXIST and os.path.isdir(statistic_folder):
        pass
      else: raise

  # search for all status files
  file_list = filter(os.path.isfile,
      glob.glob("%s/*.status.json" % status_folder)
    )
  error = warning = success = 0
  status = 'OK'
  promise_list = []
  global_state_file = os.path.join(base_folder, 'monitor.global.json')
  public_state_file = os.path.join(status_folder, 'monitor.global.json')
  for file in file_list:
    try:
      with open(file, 'r') as temp_file:
        tmp_json = json.loads(temp_file.read())
    except ValueError:
      # bad json file ?
      continue
    if tmp_json['status'] == 'ERROR':
      error  += 1
    elif tmp_json['status'] == 'OK':
      success += 1
    elif tmp_json['status'] == 'WARNING':
      warning += 1
    tmp_json['time'] = tmp_json['start-date'].split(' ')[1]
    promise_list.append(tmp_json)

  if error:
    status = 'ERROR'
  elif warning:
    status = 'WARNING'

  global_state_dict = dict(
      status=status,
      state={
        'error': error,
        'success': success,
        'warning': warning,
      },
      type='global',
      date=report_date,
      _links={"rss_url": {"href": "%s/public/feed" % base_url},
              "public_url": {"href": "%s/share/jio_public/" % base_url},
              "private_url": {"href": "%s/share/jio_private/" % base_url}
            },
      data={'state': 'monitor_state.data',
            'process_state': 'monitor_process_resource.status',
            'process_resource': 'monitor_resource_process.data',
            'memory_resource': 'monitor_resource_memory.data',
            'io_resource': 'monitor_resource_io.data',
            'monitor_process_state': 'monitor_resource.status'}
    )

  global_state_dict['_embedded'] = {'promises': promise_list}

  if os.path.exists(instance_file):
    config = ConfigParser.ConfigParser()
    config.read(instance_file)
    if 'instance' in config.sections():
      instance_dict = {}
      global_state_dict['title'] = config.get('instance', 'name')
      global_state_dict['hosting-title'] = config.get('instance', 'root-name')
      if not global_state_dict['title']:
        global_state_dict['title'] = 'Instance Monitoring'
      
      instance_dict['computer'] = config.get('instance', 'computer')
      instance_dict['ipv4'] = config.get('instance', 'ipv4')
      instance_dict['ipv6'] = config.get('instance', 'ipv6')
      instance_dict['software-release'] = config.get('instance', 'software-release')
      instance_dict['software-type'] = config.get('instance', 'software-type')
      instance_dict['partition'] = config.get('instance', 'partition')

      global_state_dict['_embedded'].update({'instance' : instance_dict})

  if related_monitor_list:
    global_state_dict['_links']['related_monitor'] = [{'href': "%s/share/jio_public" % url}
                          for url in related_monitor_list]

  if os.path.exists(parameter_file):
    with open(parameter_file) as cfile:
      global_state_dict['parameters'] = json.loads(cfile.read())

  # Public information with the link to private folder
  public_state_dict = dict(
    status=status,
    date=report_date,
    _links={'monitor': {'href': '%s/share/jio_private/' % base_url}},
    title=global_state_dict.get('title', '')
  )
  public_state_dict['hosting-title'] = global_state_dict.get('hosting-title', '')
  public_state_dict['_links']['related_monitor'] = global_state_dict['_links'].get('related_monitor', [])

  with open(global_state_file, 'w') as fglobal:
    fglobal.write(json.dumps(global_state_dict))

  with open(public_state_file, 'w') as fpglobal:
    fpglobal.write(json.dumps(public_state_dict))

  generateStatisticsData(
    os.path.join(statistic_folder, 'monitor_state.data.json'),
    global_state_dict)

  return 0

if __name__ == "__main__":
  if len(sys.argv) < 3:
    print("Usage: %s <monitor_conf_path> <instance_conf_path>" % sys.argv[0])
    sys.exit(2)
  sys.exit(main(sys.argv[1:]))
