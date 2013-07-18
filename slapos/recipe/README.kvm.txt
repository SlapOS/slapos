kvm
===

Introduction
------------

The erp5.recipe.kvm aims to integrate KVM setups and buildout. This recipe is 
able to download one remote image and setup a KVM environment to use it. 

This recipe is also capable to reuse images or partitions already present on
disk to create the setup. 

Examples
--------

The follow examples lists different kind of configurations.


KVM with Remote and gzipped Image
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    [kvm-testing-with-remote-gzip-image]
    image = http://URL/public.mdv2010.0_x86_64.qcow2.img.gz

    # md5 checks are optional
    md5_download = adcff8adcff8adcff8adcff8
    md5_image = 1a4e371a4e371a4e371a4e371a4e37

    gzip = true
    
    # Use -hda instead -drive arg
    # Default is drive (see Options below)
    image_type = hda

    ### Common Configuration below. ###
    
    # VNC is optional
    kvm_vnc = <SOME-IP>:<VNC-DISPLAY>

    # Graphic is optional
    kvm_graphic = std

    
    # Define list of redirections.
    kvm_redir =
      tcp:13480::80
    
    kvm_net =
      user,hostname=publicmandriva
      nic,model=ne2k_pci

    # This automatically create a redirection for 13456 -> 22
    ssh_port = 13456
    ssh_key_path = /path/to/mykey.key

KVM with Remote and raw Image
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    [kvm-testing-with-remote-raw-image]
    image = http://URL/public.mdv2010.0_x86_64.qcow2.img
    md5_download = 1a4e371a4e371a4e371a4e371a4e37
    md5_image = 1a4e371a4e371a4e371a4e371a4e37

    gzip = false

    ### The Rest Same configuration as previous ###

KVM with direct local Image file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This does not copy and/or download the image::

    [kvm-testing-with-local-image]

    file = /home/you/public.mdv2010.0_x86_64.qcow2.img
    md5_image = 1a4e371a4e371a4e371a4e371a4e37

    ### The Rest Same configuration as previous ###

KVM with a linux partition
~~~~~~~~~~~~~~~~~~~~~~~~~~

This does not copy and/or download the image::

    [kvm-testing-a-linux-partition]

    file = /dev/sdb

    ### The Rest Same configuration as previous ###


Options
-------


location

  When define, it does not use buildout parts directory to allocate the image.

image

  URL to a remote image. 

file 

  Use file makes recipe ignore image option. You can define a path to a image
  or partion to use. 

image_type 

  You can define how the KVM will use the image with "-hdx" or "-drive". By
  default it uses drive and the result is:

    "kvm -drive file=IMAGE,if=virtio,cache=none,boot=on ..."

  if you use image_type=hda:
     
    "kvm -hda IMAGE ..." 

gzip

  If true means the image is compressed (gzipped), and the recipe will
  uncompress the image before copy it.

md5_download

  When defined, this values is used to verify the file downloaded.

md5_image

  When defined, this values is used to verify the image generated, don't use it
  when a partition is used in file parameter.

kvm_vnc

  Define the ip-address:display used by KVM to start the VNC server. If not
  defined, no VNC port is created.

kvm_redir

  Define port redirections to the buildout.

kvm_graphic

  If defined it adds the "-vga value" at the KVM command.

kvm_net

  Define the net definitions, each value defines one "-net" in kvm command.
  Example:
  
    kvm_net =
      user,hostname=publicmandriva
      nic,model=ne2k_pci

  It generates:

    "kvm -net user,hostname=publicmandriva -net  nic,model=ne2k_pci ..."

kvm_snapshot 

  Use "-snapshot" when run a KVM. This not write the changes direct into the
  image. Default value is False.

ssh_port

  If defined creates a new redirection for port 22 and creates few script to
  connect to the instance.

ssh_hostname

  By default it uses localhost. You don't need to define this.

ssh_key_path

  Path to the ssh key used to connect without password to the image running.
  
ssh_user

  Define the server that will be used to connect to the instance. 

kvm_bin_directory

  Place where the scripts will be created. By default it uses bin-directory from
  buildout.

kvm_run_directory

   Place where the pid file will be created, by default it uses var-directory
   from buildout.


Generated Commands
------------------

Few scripts are generated to you manage your KVM instance. The scripts names are
created with the followed standard:

   KVM-PARTS-NAME-ctl

Commands usage
~~~~~~~~~~~~~~
   
KVM-PARTS-NAME-ctl (start|stop|status|restart)
  
  This script is used to manage the KVM instance.


KVM-PARTS-NAME-sendfile REMOTEFILE LOCALFILE

  Copy the local file to a remote place.

KVM-PARTS-NAME-getfile REMOTEFILE LOCALFILE

  Copy the remote file to a local place.

KVM-PARTS-NAME-runscript COMMAND

  Run a command into remote KVM computer.
