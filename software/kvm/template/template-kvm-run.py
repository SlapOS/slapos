import hashlib
import os
import socket
import subprocess
import gzip
import shutil
from random import shuffle
import glob
import re
import json
import operator
import sys
import signal
from slapos.qemuqmpclient import QemuQMPWrapper

with open(sys.argv[1]) as fh:
  parameter_dict = json.load(fh)

qemu_img_path = parameter_dict["qemu-img-path"]
qemu_path = parameter_dict["qemu-path"]
disk_size = parameter_dict["disk-size"]
disk_type = parameter_dict["disk-type"]

network_adapter = parameter_dict["network-adapter"]

qmp_socket_path = parameter_dict.get("qmp-socket-path")
vnc_socket_path = parameter_dict.get("vnc-socket-path")

nat_rules = parameter_dict.get("nat-rules")
use_tap = parameter_dict.get("use-tap").lower()
use_nat = parameter_dict.get("use-nat").lower()
set_nat_restrict = parameter_dict.get("nat-restrict")
enable_vhost = parameter_dict.get("enable-vhost").lower()
tap_interface = parameter_dict.get("tap-interface")
listen_ip = parameter_dict.get("ipv4")
mac_address = parameter_dict.get("mac-address")
tap_mac_address = parameter_dict.get("tap-mac-address")
tap_ipv6_addr = parameter_dict.get("tap-ipv6-addr")
numa_list = parameter_dict.get("numa", "").split()
pid_file_path = parameter_dict.get("pid-file")
external_disk = eval(parameter_dict['external-disk'])
etc_directory = parameter_dict.get("etc-directory").strip()
last_disk_num_f = os.path.join(etc_directory, '.data-disk-amount')
if os.path.exists(last_disk_num_f):
  with open(last_disk_num_f, 'r') as lf:
    last_amount = int(lf.readline())
else:
  last_amount = 0
instance_root = parameter_dict['instance-root']
httpd_port = int(parameter_dict["httpd-port"])
netcat_bin = parameter_dict.get("netcat-binary").strip()
cluster_doc_host = parameter_dict.get("cluster-doc-host")
cluster_doc_port = int(parameter_dict.get("cluster-doc-port"))
auto_ballooning = parameter_dict.get("auto-ballooning") in (
  'true', 'True', '1')
vm_name = parameter_dict.get("name")

# If a device (ie.: /dev/sdb) is provided, use it instead
# the disk_path with disk_format
disk_info_list = []
for disk_device_path in parameter_dict.get("disk-device-path", "").split():
  if disk_device_path.startswith("/dev/"):
    disk_info_list.append({
      'path': disk_device_path,
      'format': "raw",
      'aio': parameter_dict['disk-aio'] or 'native',
      'cache': parameter_dict['disk-cache'] or 'none',
    })

if len(disk_info_list) == 0:
  d = {}
  for k in ['path', 'format', 'aio', 'cache']:
    v = parameter_dict['disk-' + k]
    if v:
      d[k] = v
  disk_info_list.append(d)

machine_options = parameter_dict.get("machine-options", "").strip()
cpu_model = parameter_dict.get("cpu-model").strip()

logfile = parameter_dict.get("log-file")

boot_image_url_list_json_config = parameter_dict.get(
  "boot-image-url-list-json-config")
boot_image_url_select_json_config = parameter_dict.get(
  "boot-image-url-select-json-config")
virtual_hard_drive_url_json_config = parameter_dict.get(
  "virtual-hard-drive-url-json-config")
virtual_hard_drive_gzipped = parameter_dict.get(
  "virtual-hard-drive-gzipped").strip().lower()


def md5Checksum(file_path):
    with open(file_path, 'rb') as fh:
        m = hashlib.md5()
        while True:
            data = fh.read(8192)
            if not data:
                break
            m.update(data)
        return m.hexdigest()


def getSocketStatus(host, port):
  s = None
  for af, socktype, proto, canonname, sa in socket.getaddrinfo(
    host, port, socket.AF_UNSPEC, socket.SOCK_STREAM):
    try:
      s = socket.socket(af, socktype, proto)
      s.connect(sa)
      return s
    except socket.error:
      if s:
        s.close()
        s = None


# Use downloaded virtual-hard-drive-url
if len(disk_info_list) == 1 and not os.path.exists(
  disk_info_list[0]['path']) and virtual_hard_drive_url_json_config != '':
  print('Using virtual hard drive...')
  with open(virtual_hard_drive_url_json_config) as fh:
    image_config = json.load(fh)
  if image_config['error-amount'] == 0:
    image = image_config['image-list'][0]
    downloaded_image = os.path.join(
      image_config['destination-directory'], image['destination'])
    if not os.path.exists(downloaded_image):
      raise ValueError('virtual-hard-drive-url not present yet')
    # previous version was using disk in place, but here it would result with
    # redownload, so copy it
    if virtual_hard_drive_gzipped == 'true':
      try:
        with open(disk_info_list[0]['path'], 'wb') as d_fh:
          with gzip.open(downloaded_image, 'rb') as s_fh:
            shutil.copyfileobj(s_fh, d_fh)
      except Exception:
        if os.path.exists(disk_info_list[0]['path']):
          os.unlink(disk_info_list[0]['path'])
        raise
    else:
      try:
        shutil.copyfile(downloaded_image, disk_info_list[0]['path'])
      except Exception:
        if os.path.exists(disk_info_list[0]['path']):
          os.unlink(disk_info_list[0]['path'])
        raise
  else:
    raise ValueError('virtual-hard-drive-url not ready yet')

if len(disk_info_list) == 1 and not disk_info_list[0]['path'].startswith(
  "/dev/"):
  if not os.path.exists(disk_info_list[0]['path']):
    # Create disk if doesn't exist
    # XXX: move to Buildout profile
    print('Creating virtual hard drive...')
    subprocess.check_call([
      qemu_img_path, 'create', '-f', disk_info_list[0]['format'],
      disk_info_list[0]['path'], '%sG' % disk_size])
    print('Done.')
  else:
    # Migrate from old qmpbackup bitmap if needed
    image_info_dict = json.loads(subprocess.check_output([
      qemu_img_path, 'info', '--output', 'json', disk_info_list[0]['path']]))
    for bitmap in image_info_dict.get('format-specific', {}).get(
      'data', {}).get('bitmaps', []):
      if bitmap.get('name', '').startswith('qmpbackup-%s' % (disk_type,)):
        subprocess.check_call([
          qemu_img_path, 'bitmap', '--remove', disk_info_list[0]['path'],
          bitmap['name']])
        print('Removed bitmap %s' % (bitmap['name'],))

# Generate network parameters
# XXX: use_tap should be a boolean
tap_network_parameter = []
nat_network_parameter = []
numa_parameter = []
number = -1
if use_nat == 'true':
  number += 1
  rules = 'user,id=lan%s' % number
  for port in nat_rules:
    proto = 'tcp'
    rules += ',hostfwd={proto}:{hostaddr}:{hostport}-:{guestport}'.format(
      proto=proto,
      hostaddr=listen_ip,
      hostport=port + 10000,
      guestport=port
    )

  if httpd_port > 0:
    rules += ',guestfwd=tcp:10.0.2.100:80-cmd:%s %s %s' % (
      netcat_bin, listen_ip, httpd_port)
  if cluster_doc_host and cluster_doc_port > 0:
    rules += ',guestfwd=tcp:10.0.2.101:443-cmd:%s %s %s' % (
      netcat_bin, cluster_doc_host, cluster_doc_port)
  if set_nat_restrict == 'true':
    rules += ',restrict=on'
  if use_tap == 'true' and tap_ipv6_addr != '':
    rules += ',ipv6=off'
  nat_network_parameter = [
    '-netdev', rules, '-device', '%s,netdev=lan%s,mac=%s' % (
      network_adapter, number, mac_address)]
if use_tap == 'true':
  number += 1
  vhost = ''
  if enable_vhost == 'true':
    vhost = ',vhost=on'
  tap_network_parameter = [
    '-netdev', 'tap,id=lan%s,ifname=%s,script=no,downscript=no%s' % (
      number, tap_interface, vhost),
    '-device', '%s,netdev=lan%s,mac=%s' % (
      network_adapter, number, tap_mac_address)]

kvm_argument_list = [
  qemu_path, '-enable-kvm', '-name', vm_name, '-vga', 'std',
  '-smp', str(parameter_dict['smp-count']),
  '-m', '%sM' % (parameter_dict['ram-size'],),
  '-vnc', 'unix:%s,websocket=unix:%s' % (vnc_socket_path, vnc_socket_path),
  '-boot', 'order=cd,menu=on',
  '-qmp', 'unix:%s,server,nowait' % qmp_socket_path,
  '-pidfile', pid_file_path, '-msg', 'timestamp=on',
  '-D', logfile,
  '-nodefaults',
  # switch to tablet mode for the mouse to have it synced with a client
  # see https://wiki.gentoo.org/wiki/QEMU/Options#USB
  '-usbdevice', 'tablet',
]
DISK_INFO_COUNT = 1
for disk_info in disk_info_list:
  kvm_argument_list += (
    '-drive',
    'node-name=%s,file=%s,if=%s,discard=on%s' % (
      'virtual%s' % (DISK_INFO_COUNT,), disk_info['path'], disk_type,
      ''.join(',%s=%s' % x for x in disk_info.items() if x[0] != 'path'))
  )
  DISK_INFO_COUNT += 1

rgx = re.compile(r'^[\w*\,][\=\d+\-\,\w]*$')
for numa in numa_list:
  if rgx.match(numa):
    numa_parameter.extend(['-numa', numa])
kvm_argument_list += numa_parameter

if tap_network_parameter == [] and nat_network_parameter == []:
  print('Warning : No network interface defined.')
else:
  kvm_argument_list += nat_network_parameter + tap_network_parameter

# support external-disk parameter
# allow empty index if only one disk is provided
if len(external_disk) > 1:
  for key, value in external_disk.items():
    if 'index' not in value:
      raise ValueError(
        'index is missing and more than one disk is present in external-disk '
        'configuration')
for disk_info in sorted(
  external_disk.values(), key=operator.itemgetter('index')):
  if disk_info['path'].startswith('rbd:') or disk_info['path'].startswith('/'):
    path = disk_info['path']
  else:
    path = os.path.join(instance_root, disk_info['path'])

  drive_argument_list = [
    "file=%s" % (path, ),
    "if=%s" % (disk_type, ),
    "cache=%s" % (disk_info.get('cache', 'writeback'), )
  ]
  if disk_info.get('format', 'autodetect') != 'autodetect':
    drive_argument_list.append(
      "format=%s" % (disk_info['format'],)
    )
  kvm_argument_list += (
    '-drive',
    ",".join(drive_argument_list)
  )

if auto_ballooning:
  kvm_argument_list.extend(['-device', 'virtio-balloon-pci,id=balloon0'])

machine_option_list = machine_options.split(',')
if machine_options and len(machine_option_list) > 0:
  name = 'type'
  if '=' in machine_option_list[0]:
    name, val = machine_option_list[0].split('=')
  else:
    val = machine_option_list[0]
  machine_option_list[0] = 'type=%s' % val
  if name == 'type':
    machine = ''
    for option in machine_option_list:
      key, val = option.split('=')
      machine += ',%s=%s' % (key, val)

    kvm_argument_list.extend(['-machine', machine])

if cpu_model:
  rgx = re.compile(r'^[\w*\,-_][\=\d+\-\,\w]*$')
  if rgx.match(cpu_model):
    kvm_argument_list.extend(['-cpu', cpu_model])


def handle_image(config, name):
  with open(config) as fh:
    image_config = json.load(fh)
  if image_config['error-amount'] == 0:
    for image in sorted(
      image_config['image-list'], key=lambda k: k['image-number']):
      destination = os.path.join(
        image_config['destination-directory'], image['destination'])
      if os.path.exists(destination):
        kvm_argument_list.extend([
          '-drive',
          'file=%s,media=cdrom' % (destination,)
        ])
      else:
       raise ValueError('%s not ready yet' % (name,))
  else:
    raise ValueError('%s not ready yet' % (name,))


# Note: Do not get tempted to use virtio-scsi-pci, as it does not work with
#       Debian installation CDs, rendering it uninstallable
# Note: boot-image-url-list has precedence over boot-image-url-select
if boot_image_url_list_json_config:
  # Support boot-image-url-list
  handle_image(boot_image_url_list_json_config, 'boot-image-url-list')
if boot_image_url_select_json_config:
  # Support boot-image-url-select
  handle_image(boot_image_url_select_json_config, 'boot-image-url-select')


def clean_shutdown_handler(signum, frame):
  print("Gracefully stopping qemu")
  qemu_wrapper = QemuQMPWrapper(qmp_socket_path)
  qemu_wrapper._send({"execute": "quit"})
  print("Gracefully stopped qemu")


signal_list = [signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT, signal.SIGINT]
print('Starting KVM: \n %s' % ' '.join(kvm_argument_list))
# ignore signal for the subprocess
for s in signal_list:
  signal.signal(s, signal.SIG_IGN)
# start the subprocess with new session in order to escape group signal
# propagation # as it defies the whole idea of clean shutdown on SIGTERM to
# *this* process
kvm_process = subprocess.Popen(
  kvm_argument_list, restore_signals=False, start_new_session=True)
# register signals for clean shutdown
for s in signal_list:
  signal.signal(s, clean_shutdown_handler)
# forever wait
kvm_process.wait()
