slaprunner
==========

Introduction
------------

This software release is used to deploy Slaprunner instances.
Slaprunner is an all-in-one IDE used to develop and test profiles and recipes for SlapOS.

Parameters
----------

authorized-key
~~~~~~~~~~~~~~

You need to specify your SSH public key in order to connect to the SSH server of this instance.

Example of parameter XML::

  <?xml version="1.0" encoding="utf-8"?>
  <instance>
  <parameter id="authorized-key">ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCdNp7qZMVAzNc07opHshiIFDmJpYXQpetfcSgUj39a409d42PpsJElp7WsAE/x0nN6gUIoWIl7UiAlMzf6bKEJGJVSOZEPTmiJVlgK1Gp+kE0x9yNcncYg7p38Jny0daVA/NkkpAFyRsAm5kLGzyLtaCcktSvy0cJuy7WSSHU05pd1f8Y8thofE9g5t+/JA2VZvipxPkRfkFAG3aOAGLULlTImTSDFSDFGSDFG5F6mMnl7yvY2d6vEHVBu+K+aKmAwZVfCUwtSpa/tq3i2Lppjrw3UfrxbQSFHZCkzefr+u+l4YYe+tJrX7rYJYXD7LIfZfdSeFTlHFaN/yI1 user@host.local</parameter>
  </instance>

instance-amount
~~~~~~~~~~~~~~~

Optional parameter.

Default: 10
