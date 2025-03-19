deply-test
==========

Introduction
------------

This is software release to run tests on VMs, but without direct access (like
ssh) to the VM.

It is supposed to be used as backend for ERP5TestNode.

Characteristics and limitations:

 * partitions share the same user (as they access files directly)
 * this SR will be installed and instantiated only from local file system
   (like git clone)
