invmtest
========

Introduction
------------

This is software release to run tests on VMs, but without direct access (like
ssh) to the VM.

It is supposed to be used as backend for ERP5TestNode.

It uses KVM's vm-bootstrap technique internally.

TODO
====

 * finish :)
 * simplify as much as possible
 * TEST!!!!!!!
   * it re-uses KVM SR, so it has to be assured that changes in KVM SR are picked up here
 * make it replacement for ../deploy-test, then update test suites etc
 * give maximum responsibility to the consumer about how to handle what happens in the VM
