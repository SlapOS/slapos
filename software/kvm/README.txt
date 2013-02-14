kvm
===

Introduction
------------

This software release is used to deploy KVM instances, NBD instances and
Frontend instances of KVM.

For extensive parameters definition, please look at parameter-input-schema.json.

Examples
--------

The following examples listhow to request different possible instances of KVM
Software Release from slap console or command line.

KVM instance (1GB of RAM, 10GB of SSD, one core)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Note that the KVM instance will request a frontend slave instance in order
to be accessible from IPv4.

KVM instance needs a NBD to fetch disk image at first boot. Working NBD IP/port
has to be specified.

::
  myawesomekvm = request(
      software_release=kvm,
      partition_reference="myawesomekvm",
      partition_parameter_kw={
          "ndb_ip":"2a01:e35:2e27:460:e2cb:4eff:fed9:48dc",
          "ndb_port": 1024
      }
  )


KVM+ instance (2GB of RAM, 20GB of SSD, two cores)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::
  myevenmoreawesomekvm = request(
      software_release=kvm,
      partition_reference="myevenmoreawesomekvm",
      partition_parameter_kw={
          "ndb_ip":"2a01:e35:2e27:460:e2cb:4eff:fed9:48dc",
          "ndb_port": 1024
      },
      software_type="kvm+",
  )


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
