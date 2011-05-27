grid
====

slapgrid is a client of SLAPos. SLAPos provides support for deploying a SaaS
system in a minute.
Slapgrid allows you to easily deploy instances of softwares based on buildout
profiles.
For more informations about SLAP and SLAPos, please see the SLAP documentation.


Requirements
------------

A working SLAP server with informations about your computer, in order to
retrieve them.

As Vifib servers use IPv6 only, we strongly recommend an IPv6 enabled UNIX
box.

For the same reasons, Python >= 2.6 with development headers is also strongly
recommended (IPv6 support is not complete in previous releases).

For now, gcc and glibc development headers are required to build most software
releases.


Concepts
--------

Here are the fundamental concepts of slapgrid : 
A Software Release (SR) is just a software.
A Computer Partition (CP) is an instance of a Software Release.
Imagine you want to install with slapgrid some software and run it. You will
have to install the software as a Software Release, and then instantiate it,
i.e configuring it for your needs, as a Computer Partition.


How it works
------------

When run, slapgrid will authenticate to the SLAP library with a computer_id and
fetch the list of Software Releases to install or remove and Computer
Partitions to start or stop.
Then, it will process each Software Release, and each Computer Partition.
It will also periodically send to SLAP the usage report of each Computer
Partition.


Installation
------------

With easy_install::

  $ easy_install slapgrid

slapgrid needs several directories to be created and configured before being
able to run : a software releases directory, and an instances directory with
configured computer partition directory(ies).
You should create for each Computer Partition directory created a specific user
and associate it with its Computer Partition directory. Each Computer Partition
directory should belongs to this specific user, with permissions of 0750.


Usage
-----

slapgrid needs several informations in order to run. You can specify them by
adding arguments to the slapgrid command line, or by putting then in a
configuration file.
Beware : you need a valid computer resource on server side.


Examples
--------

simple example : 
Just run slapgrid:

  $ slapgrid --instance-root /path/to/instance/root --software-root
  /path/to/software_root --master-url https://some.server/some.resource
  --computer-id my.computer.id


configuration file example::

  [slapgrid]
  instance_root = /path/to/instance/root
  software_root = /path/to/software/root
  master_url = https://slapos.server/slap_service
  computer_id = my.computer.id

then run slapgrid::

  $ slapgrid --configuration-file = path/to/configuration/file

