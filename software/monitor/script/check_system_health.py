#!/usr/bin/env python

import subprocess
import os
import re
import json

cpu_command_list = ['top', '-n', '1', '-b']
mem_command_list = ['free', '-m']
head_command_list = ['head', '-n', '5']
cpu_core_cmd_list = ['nproc']

def cpu_usage(tolerance=1.5):
  # tolerance=1.5 => accept up to 1.5 =150% CPU load
  uptime_result = subprocess.check_output(['uptime'])
  line = uptime_result.strip().split(' ')
  load, load5, long_load = line[-3:]
  core_count = int(subprocess.check_output(cpu_core_cmd_list).strip())
  threshold = core_count * tolerance
  if float(long_load) > threshold:
    # display top statistics
    top = subprocess.Popen(cpu_command_list, stdout=subprocess.PIPE)
    result = subprocess.check_output(head_command_list, stdin=top.stdout)
    message = "CPU load is high: %s %s %s\n\n" % (load, load5, long_load)
    message += result
    return message

def check_last_result(file, last_value, threshold=7.0, elt_count=5):
  mem_average = 0.0
  value_list = []
  if os.path.exists(file):
    with open(file) as f:
      values = f.read()
      value_list = values.split(' ')
      size = len(value_list)
      value_list.append(str(last_value))
      if size >= elt_count:
        while len(value_list) > elt_count:
          value_list.pop(0)
        # calculate average
        average = sum([float(l) for l in value_list])/(size * 1.0)
        if average < threshold:
          mem_average = round(average, 2)
  else:
    value_list.append(str(last_value))

  with open(file, 'w') as f:
    f.write(' '.join(value_list))
  return mem_average

def memory_usage(storage_file, threshold=7.0, elt_count=5):
  mem_stats = subprocess.check_output(mem_command_list)
  result_list = mem_stats.split('\n')
  usage = re.sub('\s+', ' ', result_list[1])
  usage_real = re.sub('\s+', ' ', result_list[2])
  usage_list = usage.split(' ')
  mem_total = float(usage_list[1])
  mem_free = float(usage_real.split(' ')[-1])
  if mem_free == 0.0:
    mem_available = 0.0
  else:
    mem_available = round(mem_free * 100 / (mem_total * 1.0), 2)
  average = check_last_result(
                              storage_file,
                              mem_available,
                              threshold=threshold,
                              elt_count=elt_count)
  if average != 0.0 and average < threshold:
    # mem used at (threshold)% at least
    message = "Memory usage is high. %s%% is available (%s%% for last %s minutes).\n\n" % (
      mem_available, average, elt_count)
    message += mem_stats
    return message
  swap_usage = re.sub('\s+', ' ', result_list[3])
  swap_usage_list = swap_usage.split(' ')
  swap_total = float(swap_usage_list[1])
  swap_free = float(swap_usage_list[3])
  if swap_total > 1:
    if swap_free == 0.0:
      swap_available = 0.0
    else:
      swap_available = round(swap_free * 100 / (swap_total * 1.0), 2) * 100
    if swap_available < threshold*1.7:
      message = "Memory SWAP usage is high. %s%% is available.\n\n" % swap_available
      message += mem_stats
      return message

if __name__ == '__main__':
  if len(sys.argv) < 2:
    print "Usage: %s [cpu | mem] CONFIG_FILE [BASE_DIR]" % os.path.basename(sys.argv[0])
    exit(2)
  check_type = sys.argv[1]
  threshold = None
  if len(sys.argv) >= 3:
    config_file = sys.argv[2]
    if os.path.exists(config_file):
      with open(config_file) as f:
        try:
          threshold = float(f.read())
          if not threshold > 0:
            threshold = None
        except ValueError:
          pass

  if check_type == "cpu":
    result = cpu_usage(threshold or 1.5)
    if result:
      print result
      exit(1)
  elif check_type == "mem":
    directory = ""
    if len(sys.argv) >= 4:
      directory = sys.argv[3]
    if not os.path.exists(directory) or not os.path.isdir(directory):
      directory = os.getcwd()
    storage_file = os.path.join(directory, 'mem-usage.mo')
    result = memory_usage(storage_file, threshold=(threshold or 4.0), elt_count=10)
    if result:
      print result
      exit(1)
  else:
    exit(3)

  exit(0)