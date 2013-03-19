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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

NBD instance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This type of instance will allow to host a disk image that will be used by
any KVM instance.

::
  mynbd = request(
      software_release=kvm,
      partition_reference="mynbd",
      software_type="nbd",
  )


KVM Frontend Master Instance (will host all frontend Slave Instances)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
