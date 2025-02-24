kvm
===

Introduction
------------

This software release is used to deploy KVM.

For extensive parameters definition, please look at parameter-input-schema.json.

Examples
--------

The following examples list how to request different possible instances of KVM
Software Release from slap console or command line.

KVM instance (1GB of RAM, 10GB of SSD, one core)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Note that the KVM instance will try to request a frontend slave instance in order
to be accessible from IPv4::

  myawesomekvm = request(
      software_release=kvm,
      partition_reference="My awesome KVM",
      partition_parameter_kw={
      }
  )

See the instance-kvm-input-schema.json file for more instance parameters (cpu-count, ram-size, disk-size, etc).

KVM instance parameters:
~~~~~~~~~~~~~~~~~~~~~~~~~

- frontend-software-type (default: default)
- frontend-software-url (default: http://git.erp5.org/gitweb/slapos.git/blob_plain/HEAD:/software/apache-frontend/software.cfg)
- frontend-instance-guid
- frontend-addtional-instance-guid
- frontend-instance-name (default: VNC Frontend)

- ram-size (default: 4096)
- disk-size = (default: 40)
- disk-type (default: virtio)
      Disk size and Disk type are used if no virtual hard drive is specified.

- cpu-count (default: 2)
- cpu-options
    cpu-option is a string: [cores=cores][,threads=threads][,sockets=sockets][,maxcpus=maxcpus]
- numa
    list of numa options separate by space ex: node,nodeid=1,cpus=9-15 node,nodeid=2,cpus=1,3,7

- nat-rules (default: 22 80 443)
    For port forwarding to IPv6 of slapos partition
- use-nat (default: True)
    Add one interface using qemu User Network (NAT), this interface support nat-rules.
- use-tap (default: True)
    Add one interface that uses tap interface from the host
- enable-vhost (default: False)
    Increase network speed by enabling vhost on qemu. (To use if the module is loaded on host machine)

- virtual-hard-drive-url
    URL of qemu image to download and use by this VM. If specified, Disk size and Disk type will be ignored.
- virtual-hard-drive-md5sum
    MD5Sum of image disk to download
- virtual-hard-drive-gzipped (default: False)
    Compress image to reduce size with gzip (.gz)

- enable-http-server (default: False)
    Configure server that will help to get some files into the vm from http
    require use-nat = True
    All files in the document_root folder of the server will be accessible to the vm: http://10.0.2.100/PATH_TO_FILE
- httpd-port (default: 8081)
- authorized-key
    the public key file will be available in the VM via url http://10.0.2.100/authorized_key
- data-to-vm
    send some text content which will be accessible to the vm through the file: http://10.0.2.100/data


Resilient KVM instance
~~~~~~~~~~~~~~~~~~~~~~

Like KVM instance, but backed-up (with history) in two places::

  kvm = 'https://lab.nexedi.com/nexedi/slapos/raw/slapos-0.188/software/kvm/software.cfg'
  myresilientkvm = request(
      software_release=kvm,
      partition_reference="My resilient KVM",
      software_type="kvm-resilient",
      partition_parameter_kw={
          "-sla-0-computer_guid": "COMP-1000", # Location of the main instance (KVM)
          "-sla-1-computer_guid": "COMP-1001", # Location of the first clone
          "-sla-2-computer_guid": "COMP-1002", # Location of the second clone
      }
  )

See the instance-kvm-input-schema.json AND instance-kvm-resilient-input-schema.json AND /stack/resilient/README.txt
files for more instance parameters (cpu-count, ram-size, disk-size, specific location of clones, etc).

Then, if you want one of the two clones to takeover, you need to login into
the hosting machine, go to the partition of the clone, and invoke bin/takeover.

Technical notes
---------------

Updating boot-image-url-select
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* download the new OS installation image
* calculate it's sha512sum and store as <SHA512>
* calculate it's md5sum and store as <MD5>
* upload it to shacache
* construct download url: ``https://shacache.nxdcdn.com/<SHA512>#<MD5>``
* update the ``boot-image-url-select`` in:
   * ``instance-kvm-input-schema.json``
   * ``instance-kvm-cluster-input-schema.json``

Migration to modern external-disk parameter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Note**: ``external-disk`` and old way are mutually exclusive, thus it will
result with not starting kvm and failing partition for sake of data
consistency.

Despite ``external-disk-number``, ``external-disk-size`` and
``external-disk-format`` are supported fully until unknown moment in the
future, it's advised to migrate to external-disk parameter as soon as possible,
as slapos.core ``slapos.cfg`` ``instance_storage_home`` can become obsoleted
and removed in future versions.

**Note**: Due to how technically ``instance_storage_home`` is implemented, such
migration requires full access to the Compute Node hosting given KVM instance.

Let's imagine that there is a kvm instance which was requested with parameters::

  {
    "external-disk-number": 2,
    "external-disk-size": 10
  }

After locating the partition on proper Compute Node, the node administrator
has to find the kvm processing running there with::

  slapos node status slappartNN: | grep kvm-

The interesting part is the ``PID``, which can be used to find which disk paths
are configured for the running KVM process with::

  ps axu | grep PID | grep --color DATA

It will be possible to find two entries pointing to ``DATA`` directory in the
partition::

  -drive file=/srv/slapgrid/slappartNN/DATA/dataX/kvm_virtual_disk.qcow2,if=virtio
  -drive file=/srv/slapgrid/slappartNN/DATA/dataY/kvm_virtual_disk.qcow2,if=virtio

**Attention**: Order of the disks is important.

The administrator shall provide absolute path to both for both disks::

  readlink -f /srv/slapgrid/slappartNN/DATA/dataX/kvm_virtual_disk.qcow2 --> /<instance_storage_home>/dataX/slappartNN/kvm_virtual_disk.qcow2
  readlink -f /srv/slapgrid/slappartNN/DATA/dataY/kvm_virtual_disk.qcow2 --> /<instance_storage_home>/dataY/slappartNN/kvm_virtual_disk.qcow2

And now it will be safe to use the paths in ``external-disk`` parameter::

  {
    "external-disk": {
      "first": {
        "path": "/<instance_storage_home>/dataX/slappartNN/kvm_virtual_disk.qcow2",
        "index": 1
      },
      "second": {
        "path": "/<instance_storage_home>/dataY/slappartNN/kvm_virtual_disk.qcow2",
        "index": 2
      }
    }
  }

Of course ``external-disk-number``, ``external-disk-size`` and
``external-disk-format`` HAVE TO be removed from instance parameters before
continuing.

For now such configuration will lead to no starting kvm process, so after
parameters are updated in SlapOS Master **and** are processed on the Compute
Node The administrator shall release the images from automatic detection by
removing files:

* ``etc/.data-disk-amount``
* ``etc/.data-disk-ids``

from the partition (typically ``/srv/slapgrid/slappartNN/`` directory).

They will reappear automatically after some time, but as the old
``external-disk-amount`` approach is now disabled, they won't be updated.

The failure observed to confirm the situation can be found in
``.slappartNN_kvm-HASH.log`` with presence of message like::

  ValueError: external-disk problems: conflicts with external-disk-number = XX, conflicts with already configured disks amount XX in /srv/slapgrid/slappartNN/etc/.data-disk-amount

Where ``XX`` is the previously used ``external-disk-number`` and ``NN`` is the partition.

Fixing qmpbackup dirty bitmap
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It can happen that bin/exporter will fail with:

CRITICAL - main: Error executing backup: Bitmap 'qmpbackup-virtio0-NNN' is inconsistent and cannot be used

In such case it is required to:

 * stop the kvm
 * use qemu-img info virtual.qcow2 to find the bitmap value, it shall be qmpbackup-virtio0-NNN
 * remove the bitmap value with qemu-img bitmap --remove virtual.qcow2 qmpbackup-virtio0-NNN
 * start back the kvm
 * re-rexecute the backup with bin/exporter
 * remove FULL-*partial from backup destination

Such situation might happen when more than one exporter is running in the same time.
