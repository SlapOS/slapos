import argparse
import glob
import json
import matplotlib.pyplot as plt
import os

parser = argparse.ArgumentParser(description='Generate a graph from benchmark results.')
parser.add_argument('dir', nargs='+',
                    help='a directory where mesurestest.*.jsonl exists.')
parser.add_argument('-o', '--output', metavar='filename', required=True,
                    help='an output filename (.png, .svg etc.)')
args = parser.parse_args()

duration_list_dict = {}
conflict_list_dict = {}
deadlock_list_dict = {}

def get_deadlock_total_count(data):
  return data.get('innodb_metrics', {}).get('lock_deadlocks') or data.get('deadlock_total_count') or 0

for dir in args.dir:
  dir = dir.rstrip('/')
  path, = glob.glob(os.path.join(dir, 'measurestest.*.jsonl'))
  duration_list = []
  conflict_list = []
  deadlock_list = []
  last_data = {}
  for l in open(path).readlines():
    data = json.loads(l)
    if 'iteration_' in l:
      duration_list.append(data['step_duration_seconds'])
      conflict_list.append(data['zeo_stats']['conflicts'] - last_data['zeo_stats']['conflicts'])
      deadlock_total_count = get_deadlock_total_count(data)
      if deadlock_total_count:
        deadlock_list.append(deadlock_total_count - get_deadlock_total_count(last_data))
    last_data = data
  duration_list_dict[dir] = duration_list
  conflict_list_dict[dir] = conflict_list
  deadlock_list_dict[dir] = deadlock_list
plt.figure(figsize=(7, 10))
ax = plt.subplot(3, 1, 1)
plt.title('Duration')
for k, duration_list in duration_list_dict.items():
  plt.plot(range(len(duration_list)), duration_list, '-', label=k)
ax.set_ylim(ymin=0)
plt.legend(loc='upper right', framealpha=0.7)
ax = plt.subplot(3, 1, 2)
plt.title('ZODB Conflicts')
for k, conflict_list in conflict_list_dict.items():
  plt.plot(range(len(conflict_list)), conflict_list, '-', label=k)
ax.set_ylim(ymin=0)
plt.legend(loc='upper right', framealpha=0.7)
ax = plt.subplot(3, 1, 3)
plt.title('RDB Deadlocks')
for k, deadlock_list in deadlock_list_dict.items():
  plt.plot(range(len(deadlock_list)), deadlock_list, '-', label=k)
ax.set_ylim(ymin=0)
plt.legend(loc='upper right', framealpha=0.7)
plt.subplots_adjust(hspace=0.5)
plt.savefig(args.output)
