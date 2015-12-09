kvm
===

Introduction
------------

This software release is used to deploy KVM instances, NBD instances and
Frontend instances of KVM.

For extensive parameters definition, please look at parameter-input-schema.json.

Examples
--------

The following examples list how to request different possible instances of KVM
Software Release from slap console or command line.

KVM instance (1GB of RAM, 10GB of SSD, one core)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Note that the KVM instance will try to request a frontend slave instance in order
to be accessible from IPv4.

::
  myawesomekvm = request(
      software_release=kvm,
      partition_reference="My awesome KVM",
      partition_parameter_kw={
          "nbd-host":"ubuntu-1204.nbd.vifib.net",
      }
  )

See the instance-kvm-input-schema.json file for more instance parameters (cpu-count, ram-size, disk-size, etc).

KVM instance parameters:
~~~~~~~~~~~~~~~~~~~~~~~~~

- frontend-software-type (default: frontend)
- frontend-software-url (default: http://git.erp5.org/gitweb/slapos.git/blob_plain/refs/tags/slapos-0.92:/software/kvm/software.cfg)
- frontend-instance-guid
- frontend-instance-name (default: VNC Frontend)
- nbd-port (default: 1024)
- nbd-host
- nbd2-port (default: 1024)
- nbd2-host

- ram-size (default: 1024)
- disk-size = (default: 10)
- disk-type (default: virtio)
      Disk size and Disk type are used if no virtual hard drive is specified.

- cpu-count (default: 1)
- cpu-options
    cpu-option is a string: [cores=cores][,threads=threads][,sockets=sockets][,maxcpus=maxcpus]
- numa
    list of numa options separate by space ex: node,nodeid=1,cpus=9-15 node,nodeid=2,cpus=1,3,7

- nat-rules (default: 22 80 443)
    For port forwarding to IPv6 of slapos partition
- use-nat (default: True)
    Add one interface using qemu User Network (NAT), this interface support nat-rules.
- use-tap (default: False)
    Add One interface that use tap interface
- enable-vhost (default: False)
    Increase network speed by enabling vhost on qemu. (To use if the module is loaded on host machine)

- virtual-hard-drive-url
    URL of qemu image to download and use by this VM. If specified, Disk size and Disk type will be ignored.
- virtual-hard-drive-md5sum
    MD5Sum of image disk to download
- virtual-hard-drive-gzipped (default: False)
    Compress image to reduce size with gzip (.gz)
- hard-drive-url-check-certificate (default: True)
    if virtual-hard-drive-url use self-signed https, then specify if https certificate should be verified or not

- external-disk-number (default: 0)
    Number of additional disk to attach to this VM. Need slapformat to be configured for this feature.
- external-disk-size (default: 20)
- external-disk-format (default: qcow2)
  additional disk format. should be in this list: ['qcow2', 'raw', 'vdi', 'vmdk', 'cloop', 'qed']

- enable-http-server (default: False)
    Configure server that will help to get some files into the vm from http
    require use-nat = True
    All files in the document_root folder of the server will be accessible to the vm: http://10.0.2.100/PATH_TO_FILE
- httpd-port (default: 8081)
- authorized-key
    the public key file will be available in the VM via url http://10.0.2.100/authorized_key
- data-to-vm
    send some text content which will be accessible to the vm through the file: http://10.0.2.100/data

- keyboard-layout-language (default: fr)
    Change keyboard layout language (Change to en-us if you face some bad bihaviors)
    Language list: ['ar', 'da', 'de', 'de-ch', 'en-gb', 'en-us', 'es', 'et', 'fi',
      'fo', 'fr', 'fr-be', 'fr-ca', 'fr-ch', 'hr', 'hu', 'is', 'it', 'ja', 'lt',
      'lv', 'mk', 'nl', 'nl-be', 'no', 'pl', 'pt', 'pt-br', 'ru', 'sl', 'sv',
      'th', 'tr']

Resilient KVM instance
~~~~~~~~~~~~~~~~~~~~~

Like KVM instance, but backed-up (with history) in two places.

::
  kvm = 'http://git.erp5.org/gitweb/slapos.git/blob_plain/refs/tags/slapos-0.188:/software/kvm/software.cfg'
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


KVM Frontend Master Instance (will host all frontend Slave Instances)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This type of instance will allow to host any frontend slave instance requested
by KVM instances. Slave instances (and thus KVM instance) will be accessible
at : https://mydomain.com/instancereference .

::
  mykvmfrontend = request(
      software_release=kvm,
      partition_reference="mykvmfrontend",
      partition_parameter_kw={
          "domain":"mydomain.com"
      },
      software_type="frontend",
  )
